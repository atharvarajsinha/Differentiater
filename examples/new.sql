SELECT id, name, email
FROM users
WHERE active = 1
  AND deleted_at IS NULL
ORDER BY name;
