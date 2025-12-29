# Supabase Setup Guide

Follow these steps to set up your free Supabase database:

## 1. Create Supabase Account

1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project"
3. Sign up with GitHub, Google, or Email

## 2. Create New Project

1. Click "New Project"
2. Fill in:
   - **Name:** quendoo-mcp
   - **Database Password:** Choose a strong password (save this!)
   - **Region:** Choose closest to your Cloud Run region (us-central1)
   - **Pricing Plan:** Free

3. Click "Create new project"
4. Wait 2-3 minutes for setup

## 3. Get Connection String

1. Go to **Project Settings** (gear icon in sidebar)
2. Click **Database** in the left menu
3. Scroll to **Connection string**
4. Select **URI** tab
5. Copy the connection string (looks like):
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
   ```
6. **Replace `[YOUR-PASSWORD]`** with the password you created in step 2

## 4. Run Database Schema

1. In Supabase dashboard, click **SQL Editor** (in sidebar)
2. Click **New Query**
3. Copy and paste the entire contents of `schema.sql` from your project
4. Click **Run** (or press Ctrl+Enter)
5. You should see: "Success. No rows returned"

## 5. Verify Setup

In SQL Editor, run:
```sql
SELECT * FROM users;
```

Should return: Empty table (0 rows) - this is correct!

## Your Connection String

Format:
```
postgresql://postgres:YOUR_PASSWORD@db.xxx.supabase.co:5432/postgres
```

**SAVE THIS!** You'll need it for deployment.

## Next Steps

Once you have your connection string, return to the main terminal and we'll continue with deployment.
