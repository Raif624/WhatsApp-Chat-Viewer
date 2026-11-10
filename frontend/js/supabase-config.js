
const SUPABASE_URL = "https://dsifhafbbwkusipkrjjk.supabase.co";

const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_iXD8WMRPCYPvO7fn20ZFbA_ECiMtkoD";

// Create the Supabase client
window.supabaseClient = window.supabase.createClient(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY
);

console.log("Supabase connection initialized.");
