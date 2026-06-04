# Duplicate Field Detection Pattern

Pattern สำหรับตรวจสอบ unique field ก่อน create/update ในทุก module ที่ต้องการ

---

## ภาพรวม Flow

```
Frontend Form
  → submit (FormData)
  → Next.js Proxy Route Handler
  → NestJS Controller
      → checkDuplicationField()  ← ตรวจสอบก่อนแตะ avatar/file
      → ถ้าซ้ำ: return { ok: 0, duplicates: [...] }
      → ถ้าไม่ซ้ำ: ดำเนินการ create/update
  → Proxy อ่าน json.ok === 0 แล้วส่งผ่านตรงๆ
  → Frontend แสดง error บน input field + toast
```

---

## 1. Types (`src/common/model/app-np.model.ts`)

```ts
export interface ResultDuplicateField {
  duplicated: boolean;
  key:        string;         // ชื่อ column ใน DB เช่น 'username', 'empId', 'email'
  value:      string | null;  // ค่าที่พบซ้ำ
}
```

---

## 2. Service: `checkDuplicationField`

### วิธีที่ถูกต้อง — Direct Knex Queries (ใช้สำหรับ user module)

ใช้ `this.knex('table').where('column', value)` โดยตรง **ไม่ใช่** `findOneJoin` หรือ `findOne` abstraction

**สาเหตุ:** `findOneJoin` ใช้ object-style notation `{ 'u.username': value }` ซึ่ง Knex ตีความ key เป็น string literal ทั้งก้อน (รวม dot) แทนที่จะ split เป็น `alias.column` ทำให้ query ผิดและหา record ไม่เจอ

```ts
// user.service.ts
async checkDuplicationField(
  body: {
    username?: string | null;
    empId?:    string | null;
    email?:    string | null;
    phone?:    string | null;
  },
  excludeId?: string,  // uuid ของ record ตัวเอง ส่งเมื่อ Edit
): Promise<ResultDuplicateField[]> {
  const duplicates: ResultDuplicateField[] = [];

  if (body.username) {
    const q = this.knex('users').where('username', body.username);
    if (excludeId) q.whereNot('uuid', excludeId);
    const found = await q.first();
    if (found) duplicates.push({ duplicated: true, key: 'username', value: body.username });
  }

  if (body.empId) {
    const q = this.knex('users').where('empId', body.empId);
    if (excludeId) q.whereNot('uuid', excludeId);
    const found = await q.first();
    if (found) duplicates.push({ duplicated: true, key: 'empId', value: body.empId });
  }

  if (body.email) {
    const q = this.knex('users').where('email', body.email);
    if (excludeId) q.whereNot('uuid', excludeId);
    const found = await q.first();
    if (found) duplicates.push({ duplicated: true, key: 'email', value: body.email });
  }

  if (body.phone) {
    const q = this.knex('users').where('phone', body.phone);
    if (excludeId) q.whereNot('uuid', excludeId);
    const found = await q.first();
    if (found) duplicates.push({ duplicated: true, key: 'phone', value: body.phone });
  }

  return duplicates;
}
```

**หลักการสำคัญ:**
- ตรวจสอบทีละ field (sequential ไม่ parallel) เพื่อให้ทุก field ที่ซ้ำถูกรายงานครบ
- ตรวจสอบเฉพาะ field ที่มีค่า (truthy) — field ที่ส่งมาว่างไม่ตรวจ
- `whereNot('uuid', excludeId)` ป้องกัน self-conflict ตอน update

### วิธีเดิม — ผ่าน findOne abstraction (ใช้ใน module อื่น)

Module อื่นที่ใช้ `findOneJoin` ผ่าน `KnexService` ใช้รูปแบบนี้ (ใช้ได้กับ table ที่ไม่มี alias ปัญหา):

```ts
async checkDuplicationField(
  body: CreateXxxDto | UpdateXxxDto,
  excludeId?: string
): Promise<ResultDuplicateField[]> {
  const uniqFields = [
    { key: 'username', value: body.username, skipIfEmpty: true },
    { key: 'empId',    value: body.empId,    skipIfEmpty: true },
  ] as DuplicateFieldModel[];

  const results = await Promise.all(
    uniqFields.map(({ key, value, skipIfEmpty }) => {
      if (skipIfEmpty && !value) return Promise.resolve(false);
      return this.findOne({
        field: key as AllowFilters,
        value: value ?? '',
        mode: 'RETURN_BOOL',
        excludeFields: excludeId ? { field: 'uuid', value: excludeId } : undefined,
      });
    })
  );

  return uniqFields
    .filter((_, i) => results[i])
    .map(c => ({ duplicated: true, key: c.key, value: c.value }));
}
```

---

## 3. Controller

ตรวจสอบก่อนทำ operation ทุกอย่าง (ก่อนแตะ avatar/file)

```ts
// POST /users — Create
@Post()
@HttpCode(HttpStatus.CREATED)  // ⚠️ ส่ง HTTP 201 ทุก response รวมถึง error
async createUser(@Body() dto: CreateUserDto, @UploadedFile() avatar, @Req() req) {
  // [0] ตรวจ duplicate ก่อน
  const duplicates = await this.userService.checkDuplicationField({
    username: dto.username,
    empId:    dto.empId,
    email:    dto.email,
    phone:    dto.phone,
  });
  if (duplicates.length > 0) {
    return {
      ok:          0,
      httpStatus:  409,
      messageCode: 'USER_DUPLICATE_FIELD',
      message:     'Duplicate field detected',
      duplicates,
    };
  }
  // ... ดำเนินการต่อ
}

// PUT /users/:id — Update
@Put(':id')
@HttpCode(HttpStatus.OK)
async updateUser(@Param('id') id: string, @Body() dto: UpdateUserDto, ...) {
  // [1] หา user ก่อน
  const sterileUser = await this.userService.findOne({ field: 'uuid', value: id, ... });
  if (!sterileUser) throw new AppHttpException({ ... });

  // [1.5] ตรวจ duplicate ก่อนแตะ avatar
  const duplicates = await this.userService.checkDuplicationField(
    { username: dto.username, empId: dto.empId, email: dto.email, phone: dto.phone },
    id,  // excludeId — ยกเว้น record ตัวเอง
  );
  if (duplicates.length > 0) {
    return {
      ok:          0,
      httpStatus:  409,
      messageCode: 'USER_DUPLICATE_FIELD',
      message:     'Duplicate field detected',
      duplicates,
    };
  }
  // ... ดำเนินการต่อ
}
```

---

## 4. Response Shape

```ts
// duplicate found — ok = 0
{
  ok:          0,
  httpStatus:  409,               // อยู่ใน body เท่านั้น
  messageCode: 'XXX_DUPLICATE_FIELD',
  message:     'Duplicate field detected',
  duplicates: [
    { duplicated: true, key: 'username', value: 'john_doe' },
    { duplicated: true, key: 'email',    value: 'john@example.com' },
  ]
}

// success — ok = 1
{
  ok:          1,
  httpStatus:  201,
  messageCode: 'XXX_CREATED',
  message:     'Created successfully',
}
```

**⚠️ สำคัญมาก:**
- HTTP status จริงที่ backend ส่งกลับ = **201** (ถ้า controller มี `@HttpCode(HttpStatus.CREATED)`) หรือ **200** ทั้งคู่ — ไม่ว่าจะ success หรือ error
- `httpStatus: 409` อยู่ในตัว **body** เท่านั้น ไม่ใช่ HTTP status จริง
- ดังนั้น proxy ต้องตรวจสอบ `json.ok === 0` ไม่ใช่ `res.ok` (HTTP status)

---

## 5. Next.js Proxy Route Handler

```ts
// src/app/api/users/route.ts (POST)
export async function POST(req: NextRequest) {
  // ... forward request ไป backend
  const backendRes = await fetch(`${API_BASE}/users`, { method: 'POST', body: formData, headers: authHeaders })
  const rawJson = await backendRes.json()

  // ⚠️ ต้องตรวจ ok ใน body ก่อน — HTTP status อาจเป็น 201 ทั้งคู่
  const json = rawJson as { ok: number; duplicates?: unknown[] }
  if (json.ok === 0) {
    // ส่งผ่านตรงๆ ไม่ wrap — frontend ต้องการ duplicates array ครบถ้วน
    return NextResponse.json(rawJson, { status: 200 })
  }

  return NextResponse.json({ data: null, success: true, message: json.message }, { status: 201 })
}

// src/app/api/users/[id]/route.ts (PUT)
export async function PUT(req: NextRequest, { params }) {
  // ... forward request ไป backend
  const backendRes = await fetch(`${API_BASE}/users/${params.id}`, { method: 'PUT', body: formData, headers: authHeaders })
  const rawJson = await backendRes.json()

  const json = rawJson as { ok: number; duplicates?: unknown[] }
  if (json.ok === 0) {
    return NextResponse.json(rawJson, { status: 200 })
  }

  return NextResponse.json({ data: rawJson.user ?? null, success: true }, { status: 200 })
}
```

---

## 6. Frontend Modal — DUP Maps และ Error State

### Mapping: backend key → form field name + message

```ts
// key จาก backend response → key ใน form state
const DUP_KEY_MAP: Record<string, string> = {
  username:  'username',    // ตรงกัน
  empId:     'employeeId',  // ต่างกัน — backend ใช้ empId, form ใช้ employeeId
  email:     'email',
  phone:     'phone',
}

// key จาก backend response → error message ภาษาไทย
const DUP_MSG_MAP: Record<string, string> = {
  username:  'Username นี้ถูกใช้งานแล้ว',
  empId:     'เลขพนักงานนี้ถูกใช้งานแล้ว',
  email:     'อีเมลนี้ถูกใช้งานแล้ว',
  phone:     'เบอร์โทรนี้ถูกใช้งานแล้ว',
}
```

### Modal handleSubmit

```ts
const handleSubmit = useCallback(async (data: FormData) => {
  setLoading(true)
  try {
    const res = await fetch('/api/users', { method: 'POST', body: formData })
    const payload = await res.json()

    // ตรวจ duplicate ก่อน res.ok
    if (payload.ok === 0 && Array.isArray(payload.duplicates) && payload.duplicates.length > 0) {
      const errs: Record<string, string> = {}
      for (const d of payload.duplicates as { key: string }[]) {
        const formKey = DUP_KEY_MAP[d.key] ?? d.key
        errs[formKey] = DUP_MSG_MAP[d.key] ?? 'ข้อมูลซ้ำ'
      }
      setFieldErrors(errs)
      toast.error(Object.values(errs).join(', '))
      return  // ไม่ปิด modal
    }

    if (!res.ok) throw new Error('เพิ่มผู้ใช้งานไม่สำเร็จ')

    toast.success('เพิ่มผู้ใช้งานสำเร็จ')
    setFieldErrors({})
    onClose()
    onCreated()
  } catch (err) {
    reportError(err instanceof Error ? err : new Error(String(err)))
  } finally {
    setLoading(false)
  }
}, [...])
```

### ล้าง fieldErrors เมื่อปิด modal

```ts
const handleClose = useCallback(() => {
  setFieldErrors({})  // reset errors ก่อนปิด
  onClose()
}, [onClose])

// ปุ่ม X ต้องใช้ handleClose ไม่ใช่ onClose โดยตรง
<button onClick={handleClose}>X</button>
```

---

## 7. Form Component — Error Display

### Form รับ fieldErrors จาก modal

```ts
interface FormProps {
  fieldErrors?: Record<string, string>  // key = form field name
  // ...
}

// sync เมื่อ prop เปลี่ยน (ป้องกัน infinite loop ด้วย useRef)
const [localErrors, setLocalErrors] = useState<Record<string, string>>(fieldErrors ?? {})
const prevFieldErrors = useRef(fieldErrors)

useEffect(() => {
  if (fieldErrors !== prevFieldErrors.current) {
    prevFieldErrors.current = fieldErrors
    setLocalErrors(fieldErrors ?? {})
  }
}, [fieldErrors])

// ล้าง error ของ field นั้นเมื่อ user แก้ไข
const set = <K extends keyof FormData>(key: K, val: FormData[K]) => {
  setForm((prev) => ({ ...prev, [key]: val }))
  if (localErrors[key as string]) {
    setLocalErrors((prev) => { const n = { ...prev }; delete n[key as string]; return n })
  }
}
```

### แสดง error ใต้ input

```tsx
<div className="flex flex-col gap-1">
  <label className="text-xs text-gray-500">Username</label>
  <motion.input
    value={form.username}
    onChange={(e) => set('username', e.target.value)}
    className={localErrors.username ? inputErrCls : inputCls}  // red border เมื่อ error
  />
  {localErrors.username && (
    <p className="text-xs text-red-500 mt-0.5">{localErrors.username}</p>
  )}
</div>
```

```ts
const inputCls =
  'input input-md w-full border-gray-200 focus:outline-none focus:ring-1 ' +
  'focus:ring-[#4694D6] focus:border-[#4694D6]'

const inputErrCls =
  'input input-md w-full border-red-400 focus:outline-none focus:ring-1 ' +
  'focus:ring-red-400 focus:border-red-400'
```

---

## 8. Modules ที่ implement แล้ว

| Module | messageCode | Fields ที่ตรวจสอบ | วิธี |
|---|---|---|---|
| departments | `DEPARTMENT_DUPLICATE_FIELD` | name, code, symbol | findOne abstraction |
| staff-users | `STAFF_USER_DUPLICATE_FIELD` | empId | findOne abstraction |
| vendings | `VENDING_DUPLICATE_FIELD` | code, serialNo | findOne abstraction |
| **user (admin)** | `USER_DUPLICATE_FIELD` | username, empId, email, phone | Direct Knex queries |

---

## 9. จุดที่พลาดบ่อย

| ปัญหา | สาเหตุ | วิธีแก้ |
|---|---|---|
| ตรวจ duplicate แล้วไม่เจอทั้งที่มีอยู่ | ใช้ `findOneJoin` กับ alias เช่น `{ 'u.username': value }` — Knex ตีความผิด | ใช้ `this.knex('table').where('column', value)` โดยตรง |
| Proxy ไม่ส่ง duplicates กลับ frontend | Proxy ตรวจ `res.ok` แล้ว wrap response ใหม่ ทำให้ `duplicates` หาย | ตรวจ `json.ok === 0` แล้ว passthrough ด้วย `NextResponse.json(rawJson)` |
| Backend ไม่มี log ทั้งที่ call มา | `API_BASE_URL` ใน `.env.local` ชี้ไปที่ remote server | ตรวจ `.env.local` ให้ชี้ถูก environment |
| fieldErrors ไม่แสดงใน form | ลืม pass `fieldErrors={fieldErrors}` ใน JSX | ตรวจ props ที่ส่งจาก modal ไป form |
| กด X แล้ว errors ยังค้างอยู่ | ปุ่ม X ใช้ `onClose` โดยตรง ไม่ผ่าน `handleClose` | ทุกปุ่มที่ปิด modal ต้องใช้ `handleClose` |
