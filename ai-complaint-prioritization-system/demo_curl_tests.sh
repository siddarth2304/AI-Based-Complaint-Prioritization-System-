#!/usr/bin/env bash
set -u

# Safe local-only security smoke tests for the demo.
# Start the backend first on http://localhost:8080 and seed demo users.
# jq is optional. If jq is missing, tokens are extracted with sed as a fallback.

BASE_URL="${BASE_URL:-http://localhost:8080}"
DEMO_PASSWORD="${DEMO_PASSWORD:-DemoPass123!}"

extract_token() {
  if command -v jq >/dev/null 2>&1; then
    jq -r '.token // empty'
  else
    sed -n 's/.*"token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p'
  fi
}

login() {
  local email="$1"
  curl -s -X POST "$BASE_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"password\":\"$DEMO_PASSWORD\"}"
}

status_only() {
  curl -s -o /dev/null -w "%{http_code}\n" "$@"
}

echo "== Health check =="
curl -i "$BASE_URL/api/health"
echo

echo "== Login demo users and extract tokens =="
ADMIN_TOKEN="$(login admin@example.com | extract_token)"
STUDENT_TOKEN="$(login student1@example.com | extract_token)"
STAFF_TOKEN="$(login staff@example.com | extract_token)"
echo "admin token present: $([ -n "$ADMIN_TOKEN" ] && echo yes || echo no)"
echo "student token present: $([ -n "$STUDENT_TOKEN" ] && echo yes || echo no)"
echo "staff token present: $([ -n "$STAFF_TOKEN" ] && echo yes || echo no)"
echo

echo "== Missing token admin access, expected 401 =="
status_only "$BASE_URL/api/admin/users"
echo

echo "== Student token admin access, expected 403 =="
status_only "$BASE_URL/api/admin/users" -H "Authorization: Bearer $STUDENT_TOKEN"
echo

echo "== Staff token admin access, expected 403 =="
status_only "$BASE_URL/api/admin/users" -H "Authorization: Bearer $STAFF_TOKEN"
echo

echo "== Admin token admin access, expected 200 =="
status_only "$BASE_URL/api/admin/users" -H "Authorization: Bearer $ADMIN_TOKEN"
echo

echo "== NoSQL object injection login payload, expected no login =="
curl -i -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":{"$ne":null},"password":"anything"}'
echo

echo "== Malformed JSON login payload, expected safe 400/401 =="
curl -i -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com",'
echo

echo "== Login rate limit test, expected 401 then 429 =="
for i in {1..10}; do
  status_only -X POST "$BASE_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","password":"wrongpassword"}'
done
echo

echo "== Security headers check =="
curl -i "$BASE_URL/api/health" | sed -n '/^HTTP/p;/^X-Content-Type-Options/p;/^X-Frame-Options/p;/^Referrer-Policy/p;/^Content-Security-Policy/p;/^Strict-Transport-Security/p'
