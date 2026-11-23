# Save as regex_example.py and run: python3 regex_example.py
import re

pattern = re.compile("^([0-9]+)\\s+\\[\\[ binary.*(jpg|jpeg|png|bmp)", flags=re.MULTILINE)
test_strings = [
    ("Input 1", "7268    [[ binary data 767 KiB png 1919x1080 ]]"),
    ("Input 2", r'7273    re.compile("^([0-9]+)\\s.*binary.*(jpg|jpeg|png|bmp)", flags=re.MULTILINE)')
]

for name, input in test_strings:
    print(f"Input: {name}")
    
    match_count = 0
    
    for match_count, match in enumerate(pattern.finditer(input), start=1):
        # Process this match here. match[0] is the full match; match[1], ... are captures.
        print(f"Match {match_count}: {match[0]}")
        print(f"  Range: {match.start()}-{match.end()} (code points)")
        
        for group, value in enumerate(match.groups(), start=1):
            print(f"  Group {group}: {value if value is not None else '<unmatched>'}")
        
        for group, value in match.groupdict().items():
            print(f"  Group {group}: {value if value is not None else '<unmatched>'}")
    
    if match_count == 0:
        print("No matches.")
