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

def resolve_name(addr):
    """Try to resolve device name using hcitool as a backup."""
    try:
        result = subprocess.run(["hcitool", "name", addr], capture_output=True, text=True, timeout=2)
        name = result.stdout.strip()
        return name if name else None
    except:
        return None
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
                
                try:
                    selection_input = input("\nSelect a device by number (or Enter to exit): ").strip()
                    if not selection_input:
                        print("\nNo selection made. Exiting.")
                        return
                    
                    selection = int(selection_input) - 1
                    if 0 <= selection < len(devices):
                        target_address = devices[selection][0]
                    else:
                        print("\nInvalid selection. Exiting.")
                        return
                except ValueError:
                    print("\nInvalid input. Please enter a number. Exiting.")
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
        known_named = [d for d in known_devices if not d[1].startswith("[Unknown Device]")]
        known_unknown = [d for d in known_devices if d[1].startswith("[Unknown Device]")]
        
        if known_named:
            print("\nKnown devices (Named):")
            for idx, (addr, name) in enumerate(known_named):
                print(f"{idx + 1}: Name: {name} | Address: {addr}")

            use_known = input("\nUse one of these named devices? (yes/no/other): ").lower()
            if use_known == 'yes':
                choice = int(input("Enter number: "))
                return [known_named[choice - 1]]
            elif use_known == 'other' and known_unknown:
                print("\nKnown devices (Unknown):")
                for idx, (addr, name) in enumerate(known_unknown):
                    print(f"{idx + 1}: Address: {addr}")
                choice = int(input("Enter number: "))
                return [known_unknown[choice - 1]]
        elif known_unknown:
            use_other = input(f"\nYou have {len(known_unknown)} unknown devices saved. See them? (yes/no): ").lower()
            if use_other == 'yes':
                for idx, (addr, name) in enumerate(known_unknown):
                    print(f"{idx + 1}: Address: {addr}")
                choice = int(input("Enter number: "))
                return [known_unknown[choice - 1]]

    print("\nSelect Scan Mode:")
    print("1: Quick Scan (Classic Only, Original Method)")
    print("2: Deep Scan (Classic + BLE, with Vendor Identification)")
    scan_choice = input("Enter choice (1/2): ")

    if scan_choice == "1":
        # ORIGINAL METHOD - DO NOT EDIT
        print("\nAttempting to scan now...")
        nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True, flush_cache=True, lookup_class=True)
        device_list = []
        if len(nearby_devices) == 0:
            print("\nNo nearby devices found.")
        else:
            print("\nFound {} nearby device(s):".format(len(nearby_devices)))
            for idx, (addr, name, _) in enumerate(nearby_devices):
                device_list.append((addr, name))

        # Save the scanned devices only if they are not already in known devices
        new_devices = [device for device in device_list if device not in known_devices]
        if new_devices:
            known_devices += new_devices
            save_devices_to_file(known_devices)
            for idx, (addr, name) in enumerate(new_devices):
                print(f"{idx + 1}: Device Name: {name} | Address: {addr}")
        return device_list

    else:
        # DEEP SCAN METHOD (Nagamancayy Edition)
        print("\n[!] Starting Deep Scan (Classic + BLE) for 15 seconds...")
        unique_devices = {} # {addr: name}
        
        # 1. Classic Scan - USE ORIGINAL METHOD PARAMS
        print("Scanning Classic Bluetooth...")
        try:
            nearby_classic = bluetooth.discover_devices(duration=8, lookup_names=True, flush_cache=True, lookup_class=True)
            for addr, name, _ in nearby_classic:
                unique_devices[addr] = name if name else None
        except Exception as e:
            log.warning(f"Classic scan failed: {e}")

        # 2. BLE Scan
        print("Checking for BLE devices (iPhone/Modern Android)...")
        try:
            lescan_proc = subprocess.Popen(["sudo", "hcitool", "lescan", "--duplicates"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(5)
            os.kill(lescan_proc.pid, signal.SIGINT)
            out, _ = lescan_proc.communicate()
            
            for line in out.decode('utf-8', errors='ignore').splitlines():
                parts = line.split(maxsplit=1)
                if len(parts) >= 1 and is_valid_mac_address(parts[0]):
                    addr = parts[0]
                    name = parts[1] if len(parts) > 1 and parts[1] != "(unknown)" else None
                    if addr not in unique_devices:
                        unique_devices[addr] = name
                    elif name and unique_devices[addr] is None:
                        unique_devices[addr] = name
        except Exception as e:
            log.warning(f"BLE scan failed: {e}")

        # 3. Active Name Resolution for remaining nameless ones
        print(f"Finalizing names for {len(unique_devices)} unique devices...")
        device_list = []
        for addr, name in unique_devices.items():
            final_name = name
            
            if not final_name:
                # Try resolving via hcitool as last resort for Classic
                resolved = resolve_name(addr)
                if resolved: final_name = resolved
            
            # If still no name, use OUI guess
            display_name = final_name if final_name else f"[{get_vendor(addr)}]"
            device_list.append((addr, display_name))
        
        if not device_list:
            print("\nNo nearby devices found.")
        else:
            # SAVE DISCOVERED DEVICES IMMEDIATELY (Fix persistence)
            new_discovered = [d for d in device_list if d not in known_devices]
            if new_discovered:
                known_devices += new_discovered
                save_devices_to_file(known_devices)
                print(f"[+] Saved {len(new_discovered)} new devices to known_devices.txt")

            # Smart Filtering: Separate named from unknown
            named_devices = [d for d in device_list if not d[1].startswith("[Unknown Device]")]
            unknown_devices = [d for d in device_list if d[1].startswith("[Unknown Device]")]
            
            print("\nFound {} unique device(s) with names:".format(len(named_devices)))
            for idx, (addr, name) in enumerate(named_devices):
                print(f"{idx + 1}: Name: {name} | Address: {addr}")
            
            if unknown_devices:
                other_idx = len(named_devices) + 1
                print(f"{other_idx}: -- Show Unknown Devices ({len(unknown_devices)} items) --")
                
                try:
                    choice = input("\nSelect a device (or Enter for unknown list): ").strip()
                    if not choice: # User just pressed enter, or wants unknown
                        print("\nShowing Unknown Devices:")
                        for idx, (addr, name) in enumerate(unknown_devices):
                            print(f"{idx + 1}: Name: {name} | Address: {addr}")
                        
                        sub_choice = input(f"\nSelect an unknown device by number (1-{len(unknown_devices)}): ").strip()
                        if sub_choice.isdigit():
                            s_idx = int(sub_choice) - 1
                            if 0 <= s_idx < len(unknown_devices):
                                return [unknown_devices[s_idx]]
                        return []
                    
                    if choice.isdigit():
                        c_idx = int(choice) - 1
                        if c_idx == len(named_devices) and unknown_devices:
                            # User specifically chose the "Show Unknown" option
                            print("\nShowing Unknown Devices:")
                            for idx, (addr, name) in enumerate(unknown_devices):
                                print(f"{idx + 1}: Name: {name} | Address: {addr}")
                            sub_choice = input(f"\nSelect an unknown device by number (1-{len(unknown_devices)}): ").strip()
                            if sub_choice.isdigit():
                                s_idx = int(sub_choice) - 1
                                if 0 <= s_idx < len(unknown_devices):
                                    return [unknown_devices[s_idx]]
                            return []
                        elif 0 <= c_idx < len(named_devices):
                            return [named_devices[c_idx]]
                except ValueError:
                    pass
            
            return device_list

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
