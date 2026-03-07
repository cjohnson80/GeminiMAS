import os

def replace_in_file(filepath, old_str, new_str):
    if not os.path.exists(filepath): return
    with open(filepath, 'r') as f:
        content = f.read()
    content = content.replace(old_str, new_str)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Fixed {filepath}")

# 1. src/app/api/infrastructure/route.ts
replace_in_file('workspace/goldeneye/src/app/api/infrastructure/route.ts', '(element: any)', '(element: Record<string, unknown>)')

# 2. src/app/api/intercept/route.ts
replace_in_file('workspace/goldeneye/src/app/api/intercept/route.ts', '(item: any)', '(item: Record<string, unknown>)')

# 3. src/app/api/webcams/route.ts
replace_in_file('workspace/goldeneye/src/app/api/webcams/route.ts', '(webcam: any)', '(webcam: Record<string, unknown>)')
replace_in_file('workspace/goldeneye/src/app/api/webcams/route.ts', 'catch (error) {', 'catch (_error) {')

# 4. src/components/layout/DashboardShell.tsx
replace_in_file('workspace/goldeneye/src/components/layout/DashboardShell.tsx', '(item: any)', '(item: Record<string, unknown>)')
replace_in_file('workspace/goldeneye/src/components/layout/DashboardShell.tsx', '(layer: any)', '(layer: Record<string, unknown>)')
replace_in_file('workspace/goldeneye/src/components/layout/DashboardShell.tsx', '(l: any)', '(l: Record<string, unknown>)')

# 5. src/components/map/Map.tsx
replace_in_file('workspace/goldeneye/src/components/map/Map.tsx', 'Plane, Activity, Ship, Video, Radio', '/* removed unused icons */')
replace_in_file('workspace/goldeneye/src/components/map/Map.tsx', '{ Map as MapIcon, Plane, Activity, Ship, Video, Radio, Zap }', '{ Map as MapIcon, Zap }')
replace_in_file('workspace/goldeneye/src/components/map/Map.tsx', 'import { Map as MapIcon, Plane, Activity, Ship, Video, Radio, Zap }', 'import { Map as MapIcon, Zap }')

