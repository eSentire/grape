-- demo01 sample
-- Create the table.
DROP TABLE IF EXISTS demo01;
CREATE TABLE demo01 (
   name TEXT NOT NULL UNIQUE,
   value TEXT NOT NULL
);

-- Should always have comments.
COMMENT ON TABLE demo01 IS 'Demo01 example table of name/value pairs';
COMMENT ON COLUMN demo01.name IS 'A unique key name.';
COMMENT ON COLUMN demo01.value IS 'A key value.';

-- Populate the table.
INSERT INTO demo01 (name, value)
VALUES
  ('title', 'Demo01'),
  ('color', 'darkgreen');
