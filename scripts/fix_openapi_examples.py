import os
import re

TARGET_DIR = "src/tenxyte/views"

def run():
    for root, _, files in os.walk(TARGET_DIR):
        for f in files:
            if not f.endswith(".py"):
                continue
            filepath = os.path.join(root, f)
            with open(filepath, "r", encoding="utf-8") as fr:
                content = fr.read()

            if "OpenApiExample" not in content:
                continue
                
            # Regex to find OpenApiExample blocks
            # This is a bit tricky, let's use a simpler approach combining regex and bracket counting
            # to inject request_only=True or response_only=True based on field contents
            
            # Simple heuristic
            modified = False
            lines = content.split('\n')
            
            in_example = False
            bracket_depth = 0
            start_line = -1
            current_example_content = ""
            
            for i, line in enumerate(lines):
                if re.search(r"OpenApiExample\(", line):
                    in_example = True
                    start_line = i
                    current_example_content = ""
                    bracket_depth = line.count("(") - line.count(")")
                    current_example_content += line + "\n"
                    # If it's a single line OpenApiExample
                    if bracket_depth <= 0:
                        in_example = False
                        
                        
                elif in_example:
                    current_example_content += line + "\n"
                    bracket_depth += line.count("(") - line.count(")")
                    
                    if bracket_depth <= 0:
                        in_example = False
                        # We have the full example block.
                        if "request_only" in current_example_content or "response_only" in current_example_content:
                            continue
                            
                        # Determine if req or res
                        # Heuristic: mostly 'error', 'access', 'message', 'token' means response
                        # 'password', 'totp', etc means request
                        
                        is_res = False
                        is_req = False
                        
                        # Inspect the 'value' dict (roughly)
                        if re.search(r"['\"](?:error|details|message|access|refresh|user|status|token|backup_codes)['\"]\s*:", current_example_content):
                            is_res = True
                        if re.search(r"['\"](?:email|password|totp_code|phone_number)[\"']\s*:", current_example_content):
                            is_req = True
                            
                        if is_res and not is_req:
                            lines[start_line] = lines[start_line].replace("OpenApiExample(", "OpenApiExample(response_only=True, ")
                            modified = True
                        elif is_req and not is_res:
                            lines[start_line] = lines[start_line].replace("OpenApiExample(", "OpenApiExample(request_only=True, ")
                            modified = True
                        elif "success" in current_example_content.lower() and not is_req:
                            lines[start_line] = lines[start_line].replace("OpenApiExample(", "OpenApiExample(response_only=True, ")
                            modified = True

            if modified:
                with open(filepath, "w", encoding="utf-8") as fw:
                    fw.write('\n'.join(lines))
                print(f"Patched: {filepath}")

if __name__ == '__main__':
    run()
