import os
import re

def patch_file(filepath, replacements):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    with open(filepath, 'r') as f:
        content = f.read()
    
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Fixed {filepath}")

patch_file('workspace/goldeneye/src/app/api/infrastructure/route.ts', [
    ('(element: any)', '(element: Record<string, any>)')
])

patch_file('workspace/goldeneye/src/app/api/intercept/route.ts', [
    ('(sat: any)', '(sat: Record<string, any>)')
])

patch_file('workspace/goldeneye/src/app/api/webcams/route.ts', [
    ('(cam: any)', '(cam: Record<string, any>)'),
    ('catch (error) {', 'catch (_error) {')
])

patch_file('workspace/goldeneye/src/components/layout/DashboardShell.tsx', [
    ('(result: any)', '(result: { destination?: { index: number }, source: { index: number } })')
])

patch_file('workspace/goldeneye/src/components/map/Map.tsx', [
    ('Plane, Activity, Ship, Video, Radio, ', ''),
    ('Plane, Activity, Ship, Video, Radio', ''),
    ('// @ts-expect-error\n', '// @ts-expect-error - DeckGL typings are incomplete\n')
])
