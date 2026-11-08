---
title: Settings
---

- **Language**: English, Nepali or Spanish, for every screen; your account remembers it.
- **Daily briefing**: the hour Today's briefing is made, and your time zone (see [Today](../today/)).
- **Model**: the model apply uses, which never leaves this machine (see below).
- **Document templates**: how your documents look, and your own templates (see [Documents](../documents/)).

### Choosing a model

apply looks for local model servers on this computer. It lists each one's models with their size and context, and says which are loaded in memory now. Embedding models are listed but can't be chosen, since they can't write.

1. Pick a **Model**. It does everything: reading postings, scoring, checking and writing.
2. Optionally pick a **Writing model**: a larger model on the same server, used only for documents.
3. On a server that takes it, set how much the model reads at once (its context). More needs more memory.
4. Press **Test and use**. apply asks the model one short question first. If its answer can't be used, nothing changes. The first use loads the model, which can take a minute.

The choice takes effect at once, for everything apply does next. **Use the settings (.env)** goes back to the model in the settings. **Look again** finds a server you've just started.

No model is chosen for you. To get one, download a model in your local model server, then press **Look again**. If apply runs in a container on Linux, start the model server listening beyond localhost, so apply's container can reach it.
- **Auto**: the minimum fit and the day's limit for what it prepares (see [Auto](../auto/)).
- **Browser extension** tokens (see [The extension](../extension/)).
- **People** (the owner only): whether anyone can create an account, and who has one. Turn an account off or on, or delete it. You never see what's in someone else's account.
