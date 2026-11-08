# The demo

**John Doe**, a made-up person, and a few applications, so you can look around apply before adding your own.
Everything here is fictional: the names, the companies and the lorem ipsum text, and every link goes to
example.com.

- **`john-doe.json`:** the demo, an `apply-export/1` file.
  - It holds one job profile, three applications at different stages (two with a résumé and cover letter), a
    saved search with two scored matches, and a saved answer.
  - When it's loaded, its dates move so the newest is today.
- **`images/`:** the README's screenshots, taken with the demo on a test model server and test job boards.

## Using it

- **When you create your account**, tick **Add a sample profile to look around**. It's off unless you tick it.
- **From the command line**, for a demo account: `apply demo --email demo@example.com`.
- **Removing it:** delete the profile and applications like any others.

## Taking the screenshots again

When the screens change, from `services/frontend`:

```sh
pnpm --filter @apply/web screenshots         # web-*.png
pnpm --filter @apply/extension screenshots   # extension-*.png
```

Each starts its own throwaway stack with the demo and the fake model server, never your data.
