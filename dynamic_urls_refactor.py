import os
import re

TEST_DIRS = ['tests', 'src/tenxyte']

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content

    # Replace literal /api/v1/ with dynamic API_PREFIX
    # But only in contexts where it makes sense, e.g. tests or docs.
    if filepath.endswith('.py'):
        # For python files, we replace "/api/v1/" with f"{auth_settings.API_PREFIX}/"
        # We need to be careful. Let's just do a relatively safe regex for string literals.
        # Find "/api/v1/" or '/api/v1/' and replace with f"{api_prefix}/" and we will ensure `api_prefix` is in scope
        # Wait, the user already saw us replace /api/ with /api/v1/ in everything. Now they want dynamic.
        
        # Actually in views (src/tenxyte), /api/v1/ is mostly in docstrings.
        # So we can replace /api/v1/ with {API_PREFIX}/ in docstrings.
        pass

    # However, a simpler way is just regex.
    # We will do a manual review if needed, but a script is faster.
    
modified_count = 0
for d in TEST_DIRS:
    for root, dirs, files in os.walk(d):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = content
                
                if 'src/tenxyte' in filepath.replace('\\', '/'):
                    # mostly docstrings
                    new_content = new_content.replace('"/api/v1/', '"{API_PREFIX}/')
                    new_content = new_content.replace('\'/api/v1/', '\'{API_PREFIX}/')
                    new_content = new_content.replace(' /api/v1/', ' {API_PREFIX}/')
                else:
                    # tests
                    # replace "/api/v1/ with f"{api_prefix}/
                    # To minimize import hell, we replace "/api/v1/" with f"{api_prefix}/"
                    # and if we made a replacement, we inject the import at the top.
                    if '"/api/v1/' in new_content or "'/api/v1/" in new_content:
                        new_content = new_content.replace('"/api/v1/', 'f"{api_prefix}/')
                        new_content = new_content.replace('\'/api/v1/', 'f\'{api_prefix}/')
                        
                        # Add import if missing
                        if 'from tenxyte.conf import auth_settings' not in new_content:
                            # inject after the first bunch of imports
                            import_statement = "from tenxyte.conf import auth_settings\napi_prefix = auth_settings.API_PREFIX\n"
                            
                            # find first import
                            lines = new_content.split('\n')
                            for i, line in enumerate(lines):
                                if line.startswith('import ') or line.startswith('from '):
                                    lines.insert(i, import_statement)
                                    new_content = '\n'.join(lines)
                                    break
                
                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    modified_count += 1
                    print(f"Updated {filepath}")

print(f"Modified {modified_count} files.")
