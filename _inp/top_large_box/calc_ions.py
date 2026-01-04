import re
import math

# Read the leap.log file
with open("leap.log", "r") as file:
    for line in file:
        match = re.search(r"Volume:\s*([\d.]+)\s*A\^3", line)
        if match:
            volume = float(match.group(1))
            result = volume * 0.00009
            rounded_value = math.ceil(result)  # Round up to next integer
            
            # Write the rounded value to ions.txt
            with open("ions.txt", "w") as output_file:
                output_file.write(f"{rounded_value}\n")
            
            print(f"Extracted Volume: {volume} A^3")
            print(f"Computed Value: {result}, Rounded Up: {rounded_value} (written to ions.txt)")
            break  # Stop after finding the first match

# Update the number in tleap.in
tleap_file = "tleap.in"
with open(tleap_file, "r") as file:
    tleap_content = file.read()

# Replace the number in "addionsRand mol Na+ X Cl- X"
updated_content = re.sub(r"(addionsRand mol Na\+ )\d+( Cl- )\d+", rf"\g<1>{rounded_value}\g<2>{rounded_value}", tleap_content)

# Write back to tleap.in
with open(tleap_file, "w") as file:
    file.write(updated_content)

print(f"Updated tleap.in with new ion count: {rounded_value}")

