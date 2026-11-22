import sys
import os
import inspect

sys.path.insert(0, os.path.abspath("backend"))

try:
    from app.main import app
    from app.dependencies import get_current_user, get_db
except Exception as e:
    print(f"Error importing app: {e}")
    sys.exit(1)

routes = []

for route in app.routes:
    if not hasattr(route, "methods"):
        continue
    
    path = route.path
    methods = sorted(list(route.methods - {"HEAD", "OPTIONS"}))
    if not methods:
        continue
        
    # Skip health, metrics, actuator, swagger/openapi docs, static
    if any(skip in path for skip in ["/health", "/metrics", "/actuator", "/docs", "/openapi.json", "/redoc"]):
        continue

    endpoint_fn = getattr(route, "endpoint", None)
    
    # Check if auth is required
    requires_auth = False
    role_required = None
    
    # Check endpoint signatures & default parameters
    if endpoint_fn:
        sig = inspect.signature(endpoint_fn)
        for param in sig.parameters.values():
            default_val = str(param.default)
            if "get_current_user" in default_val:
                requires_auth = True
            if "role" in param.name.lower() or "admin" in default_val.lower():
                role_required = "admin"
                
    # Also inspect route dependencies
    for dep in getattr(route, "dependencies", []):
        dep_str = str(dep.dependency)
        if "get_current_user" in dep_str:
            requires_auth = True
        if "admin" in dep_str.lower():
            role_required = "admin"
            
    # Check path keywords
    if "/admin" in path:
        role_required = "admin"
        requires_auth = True
    elif requires_auth:
        expected_rule = "requires-auth (any authenticated user)"
    else:
        expected_rule = "public"

    if role_required:
        expected_rule = f"role-restricted ({role_required})"

    routes.append({
        "path": path,
        "methods": methods,
        "name": route.name,
        "expected_rule": expected_rule,
        "requires_auth": requires_auth or bool(role_required)
    })

# Deduplicate by path + methods
unique_routes = {}
for r in routes:
    for m in r["methods"]:
        key = (m, r["path"])
        if key not in unique_routes:
            unique_routes[key] = {
                "method": m,
                "path": r["path"],
                "name": r["name"],
                "expected_rule": r["expected_rule"]
            }

sorted_list = sorted(unique_routes.values(), key=lambda x: (x["path"], x["method"]))

print(f"TOTAL_DISCOVERED_ENDPOINTS: {len(sorted_list)}")
print("-" * 80)
for r in sorted_list:
    print(f"{r['method']:<7} {r['path']:<45} | {r['expected_rule']}")

