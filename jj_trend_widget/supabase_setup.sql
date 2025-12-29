-- Create the trends table in Supabase
CREATE TABLE IF NOT EXISTS trends (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    title TEXT NOT NULL,
    engagement_score NUMERIC NOT NULL,
    url TEXT NOT NULL,
    industry TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_trends_platform ON trends(platform);
CREATE INDEX IF NOT EXISTS idx_trends_timestamp ON trends(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trends_engagement ON trends(engagement_score DESC);

-- Enable Row Level Security (RLS) - adjust as needed
ALTER TABLE trends ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow read access (adjust based on your security needs)
-- Option 1: Allow all reads (for development)
CREATE POLICY "Allow all reads" ON trends FOR SELECT USING (true);

-- Option 2: Or use service role key instead of anon key if you want stricter access
-- In that case, you can remove RLS or create more specific policies

-- Sample data (optional - for testing)
INSERT INTO trends (platform, timestamp, title, engagement_score, url, industry) VALUES
('instagram', NOW(), 'Top 10 Fitness Tips for 2025', 15432, 'https://instagram.com/p/example1', 'Fitness'),
('tiktok', NOW() - INTERVAL '1 day', 'Viral Dance Challenge', 98765, 'https://tiktok.com/@user/video/123', 'Entertainment'),
('x', NOW() - INTERVAL '2 days', 'Tech News: AI Breakthrough', 5432, 'https://x.com/user/status/456', 'Technology'),
('instagram', NOW() - INTERVAL '3 days', 'Healthy Meal Prep Ideas', 23456, 'https://instagram.com/p/example2', 'Fitness'),
('tiktok', NOW() - INTERVAL '4 days', 'Cooking Tutorial', 45678, 'https://tiktok.com/@chef/video/789', 'Food');

