# Why API Key is NOT Entered Twice

## Your Question
**"Защо два пъти ще се въвежда Quendoo API Key?"**
(Why would the Quendoo API key be entered twice?)

## The Answer: IT'S NOT!

Here's the confusion and clarification:

## What You Enter (Just Once Each)

```
┌──────────────────────────────────────────────────────┐
│         REGISTRATION FORM (One Time)                 │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Email:              user@hotel.com                  │
│  ↑ This is for MCP SERVER authentication            │
│                                                       │
│  Password:           ●●●●●●●●                        │
│  ↑ This is for MCP SERVER authentication            │
│                                                       │
│  Quendoo API Key:    abc123xyz789                    │
│  ↑ This is for QUENDOO PMS access                   │
│  ↑ ENTERED ONCE ← ← ← ← ← ← ← ONLY TIME!           │
│                                                       │
│  [Register Button]                                   │
│                                                       │
└──────────────────────────────────────────────────────┘
```

## What Seemed Like "Twice"

When I explained the OAuth system, I mentioned:

1. **OAuth Login** (email + password)
2. **Quendoo API Key** (from registration)

### But These Are NOT The Same Thing!

```
┌─────────────────────────────────────────────────────────────┐
│                    TWO DIFFERENT SYSTEMS                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  System #1: MCP Server Authentication                       │
│  ┌────────────────────────────────────┐                    │
│  │ Email: user@hotel.com              │                    │
│  │ Password: ●●●●●●●●                 │                    │
│  │                                    │                    │
│  │ Purpose: Prove WHO you are         │                    │
│  │ System: Your MCP server            │                    │
│  └────────────────────────────────────┘                    │
│                                                              │
│  System #2: Quendoo PMS Authentication                      │
│  ┌────────────────────────────────────┐                    │
│  │ Quendoo API Key: abc123xyz789      │ ← ENTERED ONCE    │
│  │                                    │                    │
│  │ Purpose: Access Quendoo PMS data   │                    │
│  │ System: Quendoo platform           │                    │
│  └────────────────────────────────────┘                    │
│                                                              │
│  TOTAL: 3 pieces of information, entered ONCE each          │
│  NOT the same API key entered twice!                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Walkthrough

### WITHOUT OAuth (Current System)

```
Day 1:
  Claude: "Set your API key first"
  You: "Set my Quendoo API key: abc123"  ← Entry #1
  ✓ Saved for 24 hours

Day 2 (24h later):
  You: "Show my properties"
  Claude: "Error: API key expired"
  You: "Set my Quendoo API key: abc123"  ← Entry #2
  ✓ Saved for 24 hours

Day 3:
  You: "Set my Quendoo API key: abc123"  ← Entry #3

Day 4:
  You: "Set my Quendoo API key: abc123"  ← Entry #4

TOTAL: Many times (every 24 hours)
```

### WITH OAuth (New System)

```
Registration (ONCE):
  Visit: https://auth.your-server.com/register
  Fill form:
    - Email: user@hotel.com
    - Password: securepass123
    - Quendoo API Key: abc123         ← ONLY TIME YOU ENTER IT

  Click [Register]

  System saves to database:
    ✓ Email
    ✓ Password (hashed)
    ✓ Quendoo API key

  You receive: JWT token (copy this)

Configure Claude (ONCE):
  File: claude_desktop_config.json
  Add JWT token (paste from registration)

Day 1, 2, 3, 4, 5, ... 365:
  You: "Show my properties"
  ✓ Works automatically
  ✓ API key loaded from database
  ✓ NO need to re-enter

TOTAL: Once (during registration)
```

## The Confusion Explained

When I said you need to:
1. **"Register with OAuth"** → Enter email, password, API key
2. **"Use Claude"** → Uses the API key from step 1

It SOUNDED like you enter the API key twice:
- Once during registration
- Once during use

But NO! During use, the system **automatically loads** the API key from the database. You never type it again.

## Visual Proof

```
┌─────────────────────────────────────────────────────────┐
│  HOW MANY TIMES DO YOU TYPE "abc123"?                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Without OAuth:                                         │
│  Day 1: abc123  ← You type                             │
│  Day 2: abc123  ← You type                             │
│  Day 3: abc123  ← You type                             │
│  ...                                                     │
│                                                          │
│  With OAuth:                                            │
│  Registration: abc123  ← You type (ONLY TIME)          │
│  Day 1: [loaded from database automatically]           │
│  Day 2: [loaded from database automatically]           │
│  Day 3: [loaded from database automatically]           │
│  ...                                                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Summary

**Question:** Why enter Quendoo API key twice?

**Answer:** You DON'T!

- **Email/Password** = Your MCP server login (different system)
- **Quendoo API Key** = Your Quendoo PMS credential (entered once)

You enter THREE things (email, password, API key), each ONCE.

NOT the same thing twice.

## Real-World Analogy

It's like:
- **Hotel Door Key** (OAuth email/password) → Gets you into the hotel building
- **Safe Code** (Quendoo API key) → Accesses your valuables in the room

You provide BOTH at check-in (registration).
Then every day you only need your door key.
The safe code is remembered by the system.

You DON'T enter the safe code twice.
You enter door key + safe code ONCE each.

---

**Разбра ли се? (Clear now?)** 😊
