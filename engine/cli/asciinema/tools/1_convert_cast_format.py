#!/usr/bin/env python3
import json
import sys
import os


def convert_v1_to_v2(v1_data):
    """Convert asciinema v1 format to v2 format"""
    header = {
        "version": 2,
        "width": v1_data.get("width", 80),
        "height": v1_data.get("height", 24),
        "timestamp": int(v1_data.get("created", 0))
    }

    if "env" in v1_data:
        header["env"] = v1_data["env"]

    events = []
    for frame in v1_data.get("stdout", []):
        if len(frame) >= 2:
            time_offset, output = frame[0], frame[1]
            events.append([time_offset, "o", output])

    return header, events

def fix_malformed_v2(file_path):
    """Try to fix malformed v2 files"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines:
            return False, "Empty file"

        try:
            header = json.loads(lines[0].strip())
            if "version" not in header:
                return False, "Missing version in header"
        except json.JSONDecodeError as e:
            return False, f"Invalid header JSON: {e}"

        if len(lines) < 2:
            return False, "No content beyond header"

        valid_events = 0
        for _, line in enumerate(lines[1:6]):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if isinstance(event, list) and len(event) >= 3:
                    valid_events += 1
            except json.JSONDecodeError:
                continue

        if valid_events == 0:
            return False, "No valid events found"

        return True, "File appears to be valid v2 format"

    except Exception as e:
        return False, f"Error reading file: {e}"

def convert_file(input_path, output_path):
    """Convert cast file to proper v2 format"""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        if not content:
            return False, "Empty file"

        try:
            v1_data = json.loads(content)
            if isinstance(v1_data, dict) and v1_data.get("version") == 1:
                print(f"🔄 Converting v1 to v2: {os.path.basename(input_path)}")
                header, events = convert_v1_to_v2(v1_data)

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(json.dumps(header, ensure_ascii=False) + '\n')
                    for event in events:
                        f.write(json.dumps(event, ensure_ascii=False) + '\n')

                return True, "Converted from v1 to v2"
        except json.JSONDecodeError:
            pass

        lines = content.split('\n')
        if len(lines) < 2:
            return False, "Insufficient content"

        try:
            header = json.loads(lines[0])
            if not isinstance(header, dict):
                return False, "Invalid header format"

            header["version"] = 2

            valid_events = []
            for i, line in enumerate(lines[1:], 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                    if isinstance(event, list) and len(event) >= 2:
                        if len(event) == 2:
                            event = [event[0], "o", event[1]]
                        elif len(event) >= 3:
                            if not isinstance(event[1], str):
                                event[1] = "o"

                        valid_events.append(event)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Skipping invalid event on line {i+1}: {e}")
                    continue

            if not valid_events:
                return False, "No valid events found"

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(header, ensure_ascii=False) + '\n')
                for event in valid_events:
                    f.write(json.dumps(event, ensure_ascii=False) + '\n')

            return True, f"Fixed v2 format with {len(valid_events)} events"

        except json.JSONDecodeError as e:
            return False, f"JSON parsing error: {e}"

    except Exception as e:
        return False, f"Unexpected error: {e}"

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 1_convert_cast_format.py <input.cast> <output.cast>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)

    is_valid, message = fix_malformed_v2(input_file)
    if is_valid:
        print(f"✅ File is already valid: {message}")
        import shutil
        shutil.copy2(input_file, output_file)
        sys.exit(0)

    print(f"🔧 File needs conversion: {message}")

    success, result_message = convert_file(input_file, output_file)

    if success:
        print(f"✅ {result_message}")
        print(f"📁 Output saved to: {output_file}")
    else:
        print(f"❌ Conversion failed: {result_message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
