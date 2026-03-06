import os
import sys

def create_component(name, base_path):
    """
    Creates a React component with a standard structure: 
    [name]/
      ├── [name].tsx
      └── index.ts
    """
    target_dir = os.path.join(base_path, name)
    
    if os.path.exists(target_dir):
        print(f'Error: Component {name} already exists at {target_dir}')
        return

    os.makedirs(target_dir, exist_ok=True)

    # Create the component file
    tsx_content = f"""import React from 'react';

interface {name}Props {{
  className?: string;
  children?: React.ReactNode;
}}

export const {name}: React.FC<{name}Props> = ({{ className, children }}) => {{
  return (
    <div className={{className}}>
      <h1>{name} Component</h1>
      {{children}}
    </div>
  );
}};
"""
    
    with open(os.path.join(target_dir, f'{name}.tsx'), 'w') as f:
        f.write(tsx_content)

    # Create the index file for clean exports
    with open(os.path.join(target_dir, 'index.ts'), 'w') as f:
        f.write(f"export * from './{name}';\n")

    print(f'Successfully created {name} at {target_dir}')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python3 generate_component.py <ComponentName> <BasePath>')
        sys.exit(1)
    
    comp_name = sys.argv[1]
    path = sys.argv[2]
    create_component(comp_name, path)