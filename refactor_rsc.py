import os

src_page = 'workspace/goldeneye/src/app/page.tsx'
dest_shell = 'workspace/goldeneye/src/components/layout/DashboardShell.tsx'

with open(src_page, 'r') as f:
    content = f.read()

content = content.replace('export default function Home()', 'export default function DashboardShell()')

with open(dest_shell, 'w') as f:
    f.write(content)

new_page = """import DashboardShell from '@/components/layout/DashboardShell';

export default function Page() {
  return <DashboardShell />;
}
"""

with open(src_page, 'w') as f:
    f.write(new_page)

print("RSC Refactoring Complete.")
