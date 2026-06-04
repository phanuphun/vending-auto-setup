---
name: refactor-react
description: Refactor Next.js and React code to follow component-based architecture and Clean Code principles. Rewrites logic to be readable for Junior Developers — no over-abbreviation. Use when the user asks to refactor, clean up, or restructure a React/Next.js component or page.
---

# Refactor React / Next.js

Refactor the target file(s) to follow component-based architecture, Clean Code principles, and readability standards suitable for a Junior Developer. The goal is code that is easy to understand, not just short.

---

## Step 1 — Read before touching

- Read every file the user mentions.
- Identify: What does this component do? What props does it take? What state does it hold? What side effects does it run?
- List the problems you see before writing a single line of code. Report this list to the user.

Problems to look for:
- One component doing too many things (mixing fetch logic, display logic, and layout)
- Deeply nested JSX (more than 3–4 levels without extraction)
- Inline logic inside JSX that is hard to read (long ternaries, chained `&&`, complex expressions)
- Magic values (numbers, strings) that have no name
- Variable names that are too short to be meaningful (`x`, `d`, `res`, `tmp`)
- State variables whose names don't say what they hold (`const [data, setData]` → what data?)
- A single `useEffect` doing multiple unrelated things
- Props passed more than 2 levels deep without a reason
- Repeated JSX blocks that should be a shared component

---

## Step 2 — Component extraction rules

Split a component when any of these is true:
- It has its own section of the UI that can be named (e.g., `UserProfileCard`, `OrderSummaryTable`)
- It has its own piece of state or effect that doesn't belong in the parent
- The JSX block is longer than ~30 lines and has a clear logical boundary
- The same structure appears in more than one place

**Extraction naming:**
- Name the component after what it *is*, not what it *does*: `ProductCard`, not `renderProduct`
- Name sub-components with the parent prefix when they are only used inside one parent: `VendingDetailTabStats`, `VendingDetailTabOverview`
- Keep co-located components in the same file only when they are small (< 30 lines) and only used in that file. Otherwise split into a separate file.

---

## Step 3 — Clean Code rules to apply

### Naming
- Variables: describe what they hold. `isLoading`, `hasError`, `selectedVendingId`, `productList`
- Booleans: start with `is`, `has`, `can`, `should`. Never `flag`, `status`, `check`
- Event handlers: start with `handle`: `handleSubmit`, `handleTabChange`, `handleModalClose`
- Async fetch functions: start with `fetch` or `load`: `fetchProductList`, `loadVendingDetail`
- Constants: `UPPER_SNAKE_CASE` for values that never change and have a meaningful name

### Logic — write for readability, not brevity

**Do not compress logic into a single expression when a few lines are clearer.**

```tsx
// ❌ Hard to read — Junior Developers will not understand this immediately
const label = !data ? 'Loading...' : data.error ? 'Error' : data.items.length === 0 ? 'Empty' : `${data.items.length} items`

// ✅ Clear — every case is named
function getStatusLabel(data: ProductData | null): string {
    if (data === null) {
        return 'Loading...'
    }
    if (data.error) {
        return 'Error'
    }
    if (data.items.length === 0) {
        return 'Empty'
    }
    return `${data.items.length} items`
}
```

```tsx
// ❌ Anonymous inline reducer
setItems(prev => [...prev.filter(i => i.id !== id), { ...item, qty: item.qty + 1 }])

// ✅ Named helper — intent is clear
function incrementItemQuantity(items: CartItem[], targetId: string): CartItem[] {
    return items.map(item => {
        if (item.id !== targetId) {
            return item
        }
        return { ...item, qty: item.qty + 1 }
    })
}
setItems(prev => incrementItemQuantity(prev, id))
```

### State
- One `useState` per logical piece of state. Do not put unrelated values into one object unless they always change together.
- Name state and setter symmetrically: `[productList, setProductList]`, `[isModalOpen, setIsModalOpen]`
- If a derived value can be calculated from existing state, compute it during render — do not store it in state.

```tsx
// ❌ Storing derived state
const [filteredProducts, setFilteredProducts] = useState(products)
useEffect(() => { setFilteredProducts(products.filter(p => p.active)) }, [products])

// ✅ Derive during render
const activeProducts = products.filter(product => product.active)
```

### useEffect
- One `useEffect` per concern. If an effect does two unrelated things, split it into two effects.
- Always name async functions inside the effect rather than using an anonymous async function.

```tsx
// ❌ Anonymous async in useEffect
useEffect(() => {
    (async () => {
        const res = await fetch('/api/products')
        setProducts(await res.json())
    })()
}, [])

// ✅ Named inner function — clear intent, easier to debug
useEffect(() => {
    async function loadProducts() {
        const response = await fetch('/api/products')
        const data = await response.json()
        setProducts(data)
    }

    loadProducts()
}, [])
```

### JSX
- Extract any expression longer than a simple variable reference into a variable above the return.
- Avoid ternaries inside JSX when the two branches are both multi-line JSX. Use an `if` block above the return instead.
- Do not abbreviate prop names: `onChange` not `onChange={fn}` when prop drilling — use full descriptive prop names.

```tsx
// ❌ Logic buried in JSX
return (
    <div>
        {isLoading ? <Spinner /> : error ? <ErrorMessage msg={error} /> : <ProductList items={products} />}
    </div>
)

// ✅ Logic resolved before return
if (isLoading) {
    return <Spinner />
}

if (error) {
    return <ErrorMessage message={error} />
}

return (
    <div>
        <ProductList items={products} />
    </div>
)
```

### Props
- Destructure props at the function signature level.
- Define a `Props` interface (or `type`) directly above the component function.
- If a component receives more than 5–6 props, consider whether it is doing too much.

```tsx
// ✅ Props type + destructured signature
interface ProductCardProps {
    productId: string
    productName: string
    price: number
    isOutOfStock: boolean
    onAddToCart: (productId: string) => void
}

export default function ProductCard({ productId, productName, price, isOutOfStock, onAddToCart }: ProductCardProps) {
    // ...
}
```

---

## Step 4 — Next.js specific rules

### Server vs Client
- Mark a file `'use client'` only when it needs browser APIs, event handlers, or React state/effects.
- Prefer Server Components for data fetching and static rendering.
- Do not fetch data in a Client Component when a Server Component can do it instead.

### API Route Handlers
- Name the handler function after the HTTP method: `GET`, `POST`, `PUT`, `DELETE`.
- Extract request parsing and response shaping into named functions.
- Do not put business logic directly in the route handler — call a service or utility function.

### Custom Hooks
- Extract any stateful logic that is reused across two or more components into a custom hook in `src/hooks/`.
- Name hooks `use<WhatTheyManage>`: `useProductList`, `useVendingDetail`, `useAuthToken`.
- A custom hook must return a named object, not an array (unless it is intentionally a state+setter pair like `useState`).

```tsx
// ✅ Custom hook with named return
export function useVendingDetail(vendingUuid: string) {
    const [detailData, setDetailData] = useState<VendingDetail | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        async function loadVendingDetail() {
            setIsLoading(true)
            try {
                const response = await fetch(`/api/vending/${vendingUuid}/detail`)
                const result = await response.json()
                setDetailData(result.data)
            } catch (err) {
                setError('Failed to load vending detail')
            } finally {
                setIsLoading(false)
            }
        }

        if (vendingUuid) {
            loadVendingDetail()
        }
    }, [vendingUuid])

    return { detailData, isLoading, error }
}
```

---

## Step 5 — What NOT to do

- Do not add comments explaining what the code does — the names should do that.
- Do not split a component just to reduce line count. Split only when there is a clear logical or UI boundary.
- Do not add abstraction for hypothetical future use cases. Refactor what is actually there.
- Do not rename things that are already clear and consistent with the rest of the codebase.
- Do not change behavior — only structure and readability.

---

## Step 6 — JSX Tag Verification

After writing or editing any JSX/TSX file, verify tag balance before moving on.

### What to check
- Every opening tag has a matching closing tag: `<Foo>` → `</Foo>`
- Self-closing tags are correctly terminated: `<Input />` not `<Input>`
- Fragments are balanced: `<>` → `</>` and `<React.Fragment>` → `</React.Fragment>`
- Conditional renders don't accidentally leave a tag open on one branch and closed on another

### How to verify

Read through every file you modified from top to bottom. For each opening tag, mentally push it onto a stack; for each closing tag, pop and confirm the names match. If anything is mismatched, fix it immediately — do not proceed to Step 7 until all files are tag-clean.

For large files, use the Read tool to re-read the full output after editing and scan for unpaired tags.

**Common mistakes to catch:**

```tsx
// ❌ Missing closing tag
return (
    <div className="wrapper">
        <Header />
        <main>
            <ProductList items={products} />
        </main>
    // </div> forgotten
)

// ❌ Wrong closing tag name
return (
    <section>
        <ArticleCard />
    </div>   {/* should be </section> */}
)

// ❌ Fragment opened but not closed
return (
    <>
        <Foo />
        <Bar />
    // </> missing
)
```

---

## Step 7 — TypeScript Type Check

After all edits are complete and JSX tags are verified, run the TypeScript compiler to confirm no type errors were introduced.

### Determine the sub-project

Identify which sub-project the edited files belong to:

| Files under | Sub-project dir | Type-check command |
|---|---|---|
| `sterile-admin-front/` | `sterile-admin-front` | `npm run type-check` |
| `sterile-admin-api/` | `sterile-admin-api` | `npm run type-check` |
| `sterile-vending-api/` | `sterile-vending-api` | `npm run type-check` |
| `sterile-worker/` | `sterile-worker` | `npm run type-check` |
| `sterile-database-migration/` | `sterile-database-migration` | `npm run type-check` |

If the project does not have a `type-check` script, fall back to `npx tsc --noEmit`.

### Run the check

```bash
cd <sub-project-dir>
npm run type-check
```

### Handling errors

- **Zero errors** — proceed to Step 8.
- **Errors exist** — fix every error before proceeding. Do not skip or cast away errors with `as any` or `@ts-ignore` unless the error is in a third-party type definition that cannot be fixed.
- If an error is in a file you did not touch, note it separately in the Step 8 report as a pre-existing issue — do not fix it unless the user asks.

---

## Step 8 — Report changes

After applying all changes, report:
1. Which components were extracted and why
2. Which variables or functions were renamed and what they were before
3. Which `useEffect` blocks were split and why
4. Any files created or deleted
5. Anything that was intentionally left unchanged and why
6. Result of the TypeScript type check (pass / errors found and fixed / pre-existing errors noted)
