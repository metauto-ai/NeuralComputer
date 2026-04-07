#!/usr/bin/env python3
"""
Extended Arithmetic VHS Tape Generator
Generates 1000 comprehensive Python REPL arithmetic tapes covering:
- Single digit (1-9)
- Double digit (10-99) 
- Triple digit (100-999)
- Various operations: +, -, *, /, %, **
"""

import argparse
import json
import random
from pathlib import Path

from _common import (
    DEFAULT_ID_WIDTH,
    DEFAULT_START_INDEX,
    TapeIdAllocator,
    TapeMetadata,
    ensure_output_dir,
    render_tape,
)

def generate_comprehensive_arithmetic_patterns():
    """Generate comprehensive arithmetic patterns for training and testing"""
    patterns = []
    
    # 1. Single digit operations (200 patterns)
    # Addition: 1+1 to 9+9
    for a in range(1, 10):
        for b in range(1, 10):
            patterns.append({
                'expression': f'{a}+{b}',
                'category': 'single_digit_add',
                'difficulty': 1,
                'digit_type': 'single'
            })
    
    # Multiplication: 1*1 to 9*9  
    for a in range(1, 10):
        for b in range(1, 10):
            patterns.append({
                'expression': f'{a}*{b}',
                'category': 'single_digit_mul',
                'difficulty': 1,
                'digit_type': 'single'
            })
    
    # Subtraction: 2-1 to 9-8 (positive results)
    for a in range(2, 10):
        for b in range(1, a):
            patterns.append({
                'expression': f'{a}-{b}',
                'category': 'single_digit_sub',
                'difficulty': 1,
                'digit_type': 'single'
            })
    
    # 2. Double digit operations (400 patterns)
    # Two digit addition: 10+11 to 99+99 (sampled)
    double_add_samples = []
    for tens_a in range(1, 10):  # 10-90
        for tens_b in range(1, 10):  # 10-90
            for units_a in range(0, 10, 2):  # 0,2,4,6,8
                for units_b in range(0, 10, 2):  # 0,2,4,6,8
                    a = tens_a * 10 + units_a
                    b = tens_b * 10 + units_b
                    double_add_samples.append({
                        'expression': f'{a}+{b}',
                        'category': 'double_digit_add',
                        'difficulty': 2,
                        'digit_type': 'double'
                    })
    
    # Sample 150 from double digit additions
    patterns.extend(random.sample(double_add_samples, min(150, len(double_add_samples))))
    
    # Double digit multiplication: 10*10 to 99*99 (sampled)
    double_mul_samples = []
    for a in range(10, 100, 5):  # Every 5th number
        for b in range(10, 50, 3):  # Every 3rd number up to 50
            if a <= 50 or b <= 30:  # Keep results reasonable
                double_mul_samples.append({
                    'expression': f'{a}*{b}',
                    'category': 'double_digit_mul',
                    'difficulty': 3,
                    'digit_type': 'double'
                })
    
    patterns.extend(double_mul_samples[:100])  # Take first 100
    
    # Double digit subtraction
    for a in range(20, 100, 4):  # 20, 24, 28, ...
        for b in range(10, min(a, 50), 3):  # Ensure positive result
            patterns.append({
                'expression': f'{a}-{b}',
                'category': 'double_digit_sub',
                'difficulty': 2,
                'digit_type': 'double'
            })
    
    # Double digit division (exact results)
    double_div_samples = [
        (20, 2), (20, 4), (20, 5), (20, 10),
        (30, 2), (30, 3), (30, 5), (30, 6), (30, 10), (30, 15),
        (40, 2), (40, 4), (40, 5), (40, 8), (40, 10), (40, 20),
        (50, 2), (50, 5), (50, 10), (50, 25),
        (60, 2), (60, 3), (60, 4), (60, 5), (60, 6), (60, 10), (60, 12), (60, 15), (60, 20), (60, 30),
        (80, 2), (80, 4), (80, 5), (80, 8), (80, 10), (80, 16), (80, 20), (80, 40),
        (90, 2), (90, 3), (90, 5), (90, 6), (90, 9), (90, 10), (90, 15), (90, 18), (90, 30), (90, 45),
        (100, 2), (100, 4), (100, 5), (100, 10), (100, 20), (100, 25), (100, 50)
    ]
    
    for a, b in double_div_samples:
        patterns.append({
            'expression': f'{a}/{b}',
            'category': 'double_digit_div',
            'difficulty': 2,
            'digit_type': 'double'
        })
    
    # 3. Triple digit operations (200 patterns)
    # Triple digit addition
    triple_add_samples = []
    for a in range(100, 1000, 50):  # 100, 150, 200, ...
        for b in range(100, 500, 25):  # 100, 125, 150, ...
            if a + b < 1500:  # Keep results reasonable
                triple_add_samples.append({
                    'expression': f'{a}+{b}',
                    'category': 'triple_digit_add',
                    'difficulty': 3,
                    'digit_type': 'triple'
                })
    
    patterns.extend(triple_add_samples[:80])
    
    # Triple digit subtraction
    for a in range(200, 1000, 40):
        for b in range(100, min(a, 500), 30):
            patterns.append({
                'expression': f'{a}-{b}',
                'category': 'triple_digit_sub',
                'difficulty': 3,
                'digit_type': 'triple'
            })
            if len([p for p in patterns if p['category'] == 'triple_digit_sub']) >= 60:
                break
        if len([p for p in patterns if p['category'] == 'triple_digit_sub']) >= 60:
            break
    
    # Triple digit multiplication (smaller numbers)
    for a in range(100, 200, 10):
        for b in range(2, 6):
            patterns.append({
                'expression': f'{a}*{b}',
                'category': 'triple_digit_mul',
                'difficulty': 4,
                'digit_type': 'triple'
            })
    
    # Triple digit division
    triple_div_samples = [
        (100, 2), (100, 4), (100, 5), (100, 10), (100, 20), (100, 25), (100, 50),
        (200, 2), (200, 4), (200, 5), (200, 8), (200, 10), (200, 20), (200, 25), (200, 40), (200, 50), (200, 100),
        (300, 2), (300, 3), (300, 4), (300, 5), (300, 6), (300, 10), (300, 12), (300, 15), (300, 20), (300, 25), (300, 30), (300, 50), (300, 60), (300, 75), (300, 100), (300, 150),
        (400, 2), (400, 4), (400, 5), (400, 8), (400, 10), (400, 16), (400, 20), (400, 25), (400, 40), (400, 50), (400, 80), (400, 100), (400, 200),
        (500, 2), (500, 4), (500, 5), (500, 10), (500, 20), (500, 25), (500, 50), (500, 100), (500, 125), (500, 250)
    ]
    
    for a, b in triple_div_samples:
        patterns.append({
            'expression': f'{a}/{b}',
            'category': 'triple_digit_div',
            'difficulty': 3,
            'digit_type': 'triple'
        })
    
    # 4. Modulo operations (100 patterns)
    # Mixed digit modulo
    modulo_samples = []
    for a in range(5, 100, 3):
        for b in range(2, 12):
            if a > b:
                modulo_samples.append({
                    'expression': f'{a}%{b}',
                    'category': 'modulo_mixed',
                    'difficulty': 2,
                    'digit_type': 'mixed'
                })
    
    patterns.extend(modulo_samples[:80])
    
    # Large number modulo
    for a in range(100, 500, 25):
        for b in range(7, 20, 2):
            patterns.append({
                'expression': f'{a}%{b}',
                'category': 'modulo_large',
                'difficulty': 3,
                'digit_type': 'triple'
            })
            if len([p for p in patterns if p['category'] == 'modulo_large']) >= 20:
                break
        if len([p for p in patterns if p['category'] == 'modulo_large']) >= 20:
            break
    
    # 5. Power operations (50 patterns)
    power_samples = [
        (2, 2), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10),
        (3, 2), (3, 3), (3, 4), (3, 5), (3, 6),
        (4, 2), (4, 3), (4, 4), (4, 5),
        (5, 2), (5, 3), (5, 4),
        (6, 2), (6, 3),
        (7, 2), (7, 3),
        (8, 2), (8, 3),
        (9, 2), (9, 3),
        (10, 2), (10, 3), (10, 4),
        (11, 2), (12, 2), (13, 2), (14, 2), (15, 2),
        (20, 2), (25, 2)
    ]
    
    for a, b in power_samples:
        patterns.append({
            'expression': f'{a}**{b}',
            'category': 'power_operations',
            'difficulty': 4,
            'digit_type': 'power'
        })
    
    # 6. Complex expressions (50 patterns)
    complex_expressions = [
        # Single-double mixed
        '(5+3)*10', '(12-4)/2', '20+(3*4)', '(15+5)*2', '30-(2*5)',
        '(8+2)*5', '(20-8)/3', '15+(4*3)', '(10+10)/4', '25-(3*2)',
        
        # Double-double mixed  
        '(25+15)*2', '(40-10)/5', '30+(20/4)', '(50+30)/10', '60-(15*2)',
        '(35+25)/3', '(80-20)*2', '45+(30/6)', '(70+50)/6', '90-(25+5)',
        
        # Triple digit mixed
        '(100+50)/3', '200+(50*2)', '(300-100)*2', '150+(200/4)', '(250+150)/5',
        '400-(100*2)', '(500+300)/8', '600+(150/3)', '(400-200)/2', '800-(300+200)',
        
        # Mixed operations
        '2**3+10', '5**2-15', '(2**4)+20', '50-(3**2)', '(4**2)*3',
        '100+(2**3)', '(3**3)-2', '200-(5**2)', '(2**5)/4', '150+(3**2*2)',
        
        # Modulo in expressions
        '(20%7)+10', '30-(15%4)', '(25%8)*3', '40+(18%5)', '(35%6)+25'
    ]
    
    for expr in complex_expressions:
        patterns.append({
            'expression': expr,
            'category': 'complex_expressions',
            'difficulty': 5,
            'digit_type': 'complex'
        })
    
    return patterns

def generate_python_arithmetic_tape(
    tape_id: str,
    output_name: str,
    arithmetic_pattern: dict,
) -> str:
    """Generate a VHS tape for a Python arithmetic session."""
    expr = arithmetic_pattern["expression"]
    category = arithmetic_pattern["category"]
    difficulty = arithmetic_pattern["difficulty"]
    digit_type = arithmetic_pattern["digit_type"]

    instruction = (
        f"Python REPL arithmetic demonstration: `{expr}` "
        f"({category}, {digit_type} digits, difficulty {difficulty}). "
        "User starts Python interactive mode, calculates the expression, and exits after viewing the result."
    )

    body = [
        "Sleep 200ms",
        'Type "python"',
        "Enter",
        "Sleep 1s",
        f'Type "{expr}"',
        "Enter",
        "Sleep 800ms",
        'Type "exit()"',
        "Enter",
        "Sleep 500ms",
    ]

    metadata = TapeMetadata(
        tape_id=tape_id,
        instruction=instruction.replace('"', '\\"').replace("\\", "\\\\"),
        active_classes={"Exec": True},
        level=min(difficulty, 3),
        interactive=False,
        events=6,
        visual_complexity=30,
        requires=["Require python"],
        body_lines=body,
        output_name=output_name,
    )
    return render_tape(metadata)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("engine/cli/vhs/generated/arithmetic"),
        help="Directory for generated tapes",
    )
    parser.add_argument("--count", type=int, default=1000, help="Number of tapes to emit")
    parser.add_argument("--seed", type=int, default=2024, help="Random seed for sampling")
    parser.add_argument("--id-prefix", default="sft", help="Prefix for generated tape IDs")
    parser.add_argument(
        "--start-index",
        type=int,
        default=DEFAULT_START_INDEX,
        help="Starting numeric index for tape IDs (inclusive)",
    )
    parser.add_argument(
        "--id-width",
        type=int,
        default=DEFAULT_ID_WIDTH,
        help="Zero-padding width for the numeric portion of tape IDs",
    )
    return parser.parse_args()


def main() -> None:
    """Generate comprehensive arithmetic VHS tapes and a summary file."""
    args = parse_args()
    if args.count <= 0:
        raise SystemExit("--count must be positive")

    random.seed(args.seed)

    print("Generating comprehensive arithmetic VHS tapes...")
    patterns = generate_comprehensive_arithmetic_patterns()
    print(f"Generated {len(patterns)} arithmetic patterns before sampling")

    if len(patterns) < args.count:
        needed = args.count - len(patterns)
        multiplier = (needed // len(patterns)) + 1
        patterns.extend((patterns * multiplier)[:needed])
    elif len(patterns) > args.count:
        patterns = patterns[: args.count]

    print(f"Using {len(patterns)} patterns for tape generation")

    output_dir = args.output_dir
    ensure_output_dir(output_dir)

    allocator = TapeIdAllocator(
        prefix=args.id_prefix,
        start_index=args.start_index,
        width=args.id_width,
    )

    for index, pattern in enumerate(patterns, start=1):
        tape_id, output_name = allocator.next()
        content = generate_python_arithmetic_tape(tape_id, output_name, pattern)
        destination = output_dir / f"{tape_id}.tape"
        destination.write_text(content, encoding="utf-8")
        if index % 100 == 0:
            print(f"Generated {index}/{args.count} files...")

    print(f"\nSuccessfully generated {len(patterns)} comprehensive arithmetic VHS tapes!")
    print(f"Files saved to: {output_dir}")
    print(f"Next available index: {allocator.next_index}")

    summary = {
        "total_patterns": len(patterns),
        "patterns_by_category": {},
        "patterns_by_digit_type": {},
        "patterns_by_difficulty": {},
        "sample_patterns_by_type": {},
        "id_prefix": allocator.prefix,
        "starting_index": args.start_index,
        "next_available_index": allocator.next_index,
    }

    for pattern in patterns:
        cat = pattern["category"]
        dtype = pattern["digit_type"]
        diff = pattern["difficulty"]

        summary["patterns_by_category"][cat] = summary["patterns_by_category"].get(cat, 0) + 1
        summary["patterns_by_digit_type"][dtype] = summary["patterns_by_digit_type"].get(dtype, 0) + 1
        summary["patterns_by_difficulty"][diff] = summary["patterns_by_difficulty"].get(diff, 0) + 1

        bucket = summary["sample_patterns_by_type"].setdefault(dtype, [])
        if len(bucket) < 5:
            bucket.append(pattern["expression"])

    summary["testing_suggestions"] = {
        "unseen_large_numbers": ["2345+6789", "9876-1234", "456*789", "12345/25"],
        "unseen_complex_expressions": ["(1000+2000)*3-500", "2**15+100", "(5000-1000)/16"],
        "unseen_edge_cases": ["1000%37", "15**3", "(999+1)**2", "10000/125"],
        "cross_digit_combinations": ["9+100", "50*200", "1000-7", "888/8"],
    }

    summary_file = output_dir / "comprehensive_arithmetic_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Comprehensive arithmetic summary saved to: {summary_file}")

    print("\nPattern Distribution:")
    print(f"By digit type: {summary['patterns_by_digit_type']}")
    print(f"By difficulty: {summary['patterns_by_difficulty']}")
    print(f"Total categories: {len(summary['patterns_by_category'])}")


if __name__ == "__main__":
    main()
