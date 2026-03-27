import os, bluetooth,re, subprocess, time, curses, signal
import logging as log

# Vendor OUI Dictionary for Identification
VENDORS = {
    "34:AB:37": "Apple/iPhone?", "AC:3C:0B": "Apple/iPhone?", "F0:D1:A9": "Apple/iPhone?",
    "00:1A:7D": "CSR Dongle?", "BC:D1:D3": "Samsung?", "94:8B:C1": "Samsung?",
    "D8:6C:63": "Google/Pixel?", "CC:F9:E8": "Xiaomi?", "8C:85:90": "Huawei?",
}

def get_vendor(mac):
    prefix = mac.upper()[:8]
    return VENDORS.get(prefix, "Unknown Device")
def get_target_address():
    target_address = input("\nWhat is the target address? Leave blank and we will scan for you: ")

    if target_address == "":
        devices = scan_for_devices()
        if devices:
            # Check if the returned list is from known devices or scanned devices
            if len(devices) == 1 and isinstance(devices[0], tuple) and len(devices[0]) == 2:
                # A single known device was chosen, no need to ask for selection
                # I think it would be better to ask, as sometimes I do not want to chose this device and actually need solely to scan for actual devices.
                confirm = input(f"Would you like to enter this device :\n{devices[0][1]} {devices[0][0]} ? (y/n)\n").strip().lower()
                if confirm == 'y' or confirm == 'yes':
                    return devices[0][0]
                elif confirm != 'y' or 'yes':
                    return
            else:
                # Show list of scanned devices for user selection
                for idx, (addr, name) in enumerate(devices):
                    print(f"{idx + 1}: Device Name: {name}, Address: {addr}")
                selection = int(input("\nSelect a device by number: ")) - 1
                if 0 <= selection < len(devices):
                    target_address = devices[selection][0]
                else:
                    print("\nInvalid selection. Exiting.")
                    return
        else:
            return
    elif not is_valid_mac_address(target_address):
        print("\nInvalid MAC address format. Please enter a valid MAC address.")
        return

    return target_address

def restart_bluetooth_daemon():
    run(["sudo", "service", "bluetooth", "restart"])
    time.sleep(0.5)

def run(command):
    assert(isinstance(command, list))
    log.info("executing '%s'" % " ".join(command))
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result

def print_fancy_ascii_art():

    ascii_art = """
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⣀⣄⣤⣤⣄⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣴⡶⠟⠛⠉⠉⠉⠉⠉⠉⠉⠉⠉⠙⠛⠷⢶⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⠟⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⢷⣤⡀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣆⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣧⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⣠⣤⣤⣤⣤⣤⣄⣀⡀⠀⠀⢹⣧⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⣶⣶⣿⣷⣶⠶⠛⠛⠛⠛⠳⢶⣦⠀⠀⠀⠀⢠⣾⣿⣿⣿⣿⣿⣯⠉⠉⠉⠉⠉⠛⣷⠀⠀⢿⡄⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⢀⣠⣿⣀⡀⠀⠀⢿⣿⣿⣿⣿⣿⣿⣿⠀⢀⣀⣀⣤⣴⠟⠀⠀⠸⣧⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⣙⣿⣿⣿⣿⣿⣿⠶⠶⠶⠿⠛⠛⠛⠛⠛⠛⢷⣦⡀⠉⠙⠛⠛⠛⠛⠛⠛⠛⠋⠉⠁⠀⠀⠀⠀⠀⣿⠀⠀⠀
⠀⢀⣠⣴⠶⠾⠛⠛⠛⠉⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡀⠀⠀
⢠⣿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢗⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀
⠈⢿⣦⣄⣀⣀⠀⠀⢀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣤⣤⣤⣄⣀⠀⠀⠀⢸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀
⠀⠀⠈⠉⠛⠛⠛⢻⣟⠛⠛⠛⠛⠛⠋⠉⠉⠉⠉⠉⠉⠉⠉⠉⠻⠷⠀⢀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠛⠷⢶⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣴⠶⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠉⠉⢹⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡇⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⡇⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣇⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣿⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣆⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠻⢶
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⡟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⡾⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣴⠟⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⢀⣤⣤⡀⢀⣤⣤⡀⠀⣤⠀⠀⢀⣤⣄⢀⣤⣤⡀⠀⠀⣤⠀⠀⣠⠀⢀⣄⠀⠀⣠⣤⡀⠀⠀⠀⡀⠀⣠⡀⣠⣤⣤⣠⡀⠀⣤⢀⣤⣤⡀⣤⣤⡀
⢸⣯⣹⡗⣿⣿⡏⠀⣼⣿⣇⢰⡿⠉⠃⣿⣿⡍⠀⠀⠀⢿⣤⣦⣿⠀⣾⢿⡆⢾⣯⣝⡃⠀⠀⢰⣿⣆⣿⡧⣿⣽⡍⠘⣷⣸⡏⣾⣿⡯⢸⣯⣩⡿
⢸⡟⠉⠀⢿⣶⣶⢰⡿⠟⢻⡾⢷⣴⡆⢿⣶⣶⠄⠀⠀⠸⡿⠻⡿⣼⡿⠟⢿⢤⣭⣿⠟⠀⠀⢸⡇⠻⣿⠃⣿⣼⣶⠀⢻⡟⠀⢿⣧⣶⠸⣿⠻⣧
⠀⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⢀⡀⠀⠀⠀⠀⣀⠀⠀⠀⠀⣀⡀⠈⢀⣀⣀⠀⣁⣀⣀⢀⡀⠀⢀⣀⠀⠀⠀⠀⢀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⠀⢠⣧⡀⣿⠀⠀⠀⣼⡿⢿⣄⣼⡟⢿⡿⠿⣿⠿⢻⣧⢠⡿⠿⣧⣀⣿⡄⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⣿⣿⣧⣾⡟⣷⣿⠀⠀⠘⣿⣀⣸⡟⢹⡿⠟⠁⠀⣿⡀⢸⣏⢿⣇⣠⣿⢻⣏⢿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠛⠁⠀⠙⠙⠁⠘⠋⠀⠀⠀⠈⠉⠉⠀⠘⠁⠀⠀⠀⠉⠁⠈⠁⠀⠉⠉⠁⠈⠋⠈⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"""

    print("\033[1;36m" + ascii_art + "\033[0m")  # Cyan color

def clear_screen():
    os.system('clear')

# Function to save discovered devices to a file
def save_devices_to_file(devices, filename='known_devices.txt'):
    with open(filename, 'w') as file:
        for addr, name in devices:
            file.write(f"{addr},{name}\n")

def get_yes_no():
    stdscr = curses.initscr()
    curses.cbreak()
    stdscr.keypad(1)

    while True:
        key = stdscr.getch()
        if key == ord('y'):
            response = 'yes'
            break
        elif key == ord('n'):
            response = 'no'
            break

    curses.endwin()
    return response

# Function to scan for devices
def scan_for_devices():
    main_menu()

    # Load known devices
    known_devices = load_known_devices()
    if known_devices:
        print("\nKnown devices:")
        for idx, (addr, name) in enumerate(known_devices):
            print(f"{idx + 1}: Device Name: {name} | Address: {addr}")

        use_known_device = input("\nDo you want to use one of these known devices? (yes/no): ")
        if use_known_device.lower() == 'yes':
            device_choice = int(input("Enter the number of the device: "))
            return [known_devices[device_choice - 1]]

    print("\n[!] Starting Deep Scan (Classic + BLE) for 15 seconds...")
    unique_devices = {} # Use dict to maintain uniqueness {addr: name}

    # 1. Classic Scan via PyBluez
    try:
        nearby_classic = bluetooth.discover_devices(duration=8, lookup_names=True, flush_cache=True)
        for addr, name in nearby_classic:
            unique_devices[addr] = name if name else f"[{get_vendor(addr)}]"
    except Exception as e:
        log.warning(f"Classic scan failed: {e}")

    # 2. BLE Scan via hcitool (Passive/Active)
    print("Checking for BLE devices (iPhone/Modern Android)...")
    try:
        # Run lescan for a short duration
        lescan_proc = subprocess.Popen(["sudo", "hcitool", "lescan", "--duplicates"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(5)
        os.kill(lescan_proc.pid, signal.SIGINT)
        out, _ = lescan_proc.communicate()
        
        for line in out.decode('utf-8', errors='ignore').splitlines():
            # Format: MAC NAME or just MAC
            parts = line.split(maxsplit=1)
            if len(parts) >= 1 and is_valid_mac_address(parts[0]):
                addr = parts[0]
                name = parts[1] if len(parts) > 1 and parts[1] != "(unknown)" else None
                
                if addr not in unique_devices or (unique_devices[addr].startswith("[") and name):
                    unique_devices[addr] = name if name else f"[{get_vendor(addr)}]"
    except Exception as e:
        log.warning(f"BLE scan failed: {e}")

    device_list = [(addr, name) for addr, name in unique_devices.items()]
    
    if not device_list:
        print("\nNo nearby devices found.")
    else:
        # We only show devices that have a name OR were identified by OUI as a known vendor
        print("\nFound {} unique device(s):".format(len(device_list)))
        filtered_list = []
        for addr, name in device_list:
            # Re-filtering: if it has a real name or is a recognized vendor, it stays. 
            # Otherwise we keep it but it might be "Unknown Device"
            filtered_list.append((addr, name))
            
        for idx, (addr, name) in enumerate(filtered_list):
            print(f"{idx + 1}: Name: {name} | Address: {addr}")
        
        # Update known devices with unique new ones
        new_devices = [d for d in filtered_list if d not in known_devices]
        if new_devices:
            save_devices_to_file(known_devices + new_devices)
            
        return filtered_list

    return []

def print_menu():
    title = "BlueDucky - Bluetooth Device Attacker"
    separator = "=" * 70
    print("\033[1;35m" + separator)  # Purple color for separator
    print("\033[1;33m" + title.center(len(separator)))  # Yellow color for title
    print("\033[1;35m" + separator + "\033[0m")  # Purple color for separator
    print("\033[1;32m" + "卄ﾑ𝖈𝗸╰Ꮗⁱ‿ᵗ𝔥╯ﾑ𝗸𝗸！| you can still attack devices without visibility..." + "\033[0m")
    print("\033[1;32m" + "If you have their MAC address..." + "\033[0m")
    print("\033[1;35m" + separator + "\033[0m")  # Purple color for separator

def main_menu():
    clear_screen()
    print_fancy_ascii_art()
    print_menu()


def is_valid_mac_address(mac_address):
    # Regular expression to match a MAC address in the form XX:XX:XX:XX:XX:XX
    mac_address_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    return mac_address_pattern.match(mac_address) is not None

# Function to read DuckyScript from file
def read_duckyscript(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return [line.strip() for line in file.readlines()]
    else:
        log.warning(f"File {filename} not found. Skipping DuckyScript.")
        return None

# Function to load known devices from a file
def load_known_devices(filename='known_devices.txt'):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return [tuple(line.strip().split(',')) for line in file]
    else:
        return []
