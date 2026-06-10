# TypeScript skill

- No `any` — use `unknown` and narrow with type guards
- Define explicit interfaces for all props and API response shapes
- Use discriminated unions for state machines (`type Status = "idle" | "loading" | "error" | "success"`)
- Prefer `type` over `interface` for unions/intersections; use `interface` for object shapes
- Always type async function return values: `async function fetchUser(): Promise<User>`
- Enable strict mode in tsconfig
