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

def get_services(addr):
    """Retrieve UUID/Services and RSSI with improved reliability."""
    print(f"\n[!] Performing Discovery for {addr}...")
    
    # 1. Try bluetoothctl info first (Fastest/Cached)
    print("Checking cached info via bluetoothctl...")
    try:
        info_proc = subprocess.run(["bluetoothctl", "info", addr], capture_output=True, text=True, timeout=3)
        if "UUID:" in info_proc.stdout:
            print("\n--- Cached Services/UUIDs ---")
            for line in info_proc.stdout.splitlines():
                if "UUID:" in line or "Name:" in line or "Alias:" in line:
                    print(line.strip())
    except:
        pass

    # 2. Try to get RSSI
    try:
        print("\nChecking signal strength (RSSI)...")
        # Try btmgmt find for a fresh look
        rssi_proc = subprocess.run(["sudo", "btmgmt", "find"], capture_output=True, text=True, timeout=3)
        for line in rssi_proc.stdout.splitlines():
            if addr.upper() in line.upper() and "rssi" in line.lower():
                print(f"[+] Current RSSI: {line.split('rssi')[-1].split()[0]} dBm")
                break
    except:
        pass

    # 3. Try Active GATT scan
    try:
        print("\nScanning Live GATT Services (this may take a moment)...")
        # Increased timeout and added connection retry
        result = subprocess.run(["sudo", "gatttool", "-b", addr, "--primary"], capture_output=True, text=True, timeout=10)
        if result.stdout:
            print("--- Primary Services (GATT) ---")
            print(result.stdout.strip())
        else:
            # Fallback to PyBluez discovery if gatttool fails/times out
            print("[!] gatttool returned nothing, trying PyBluez discovery...")
            services = bluetooth.find_service(address=addr)
            if services:
                for svc in services:
                    print(f"Service: {svc.get('name', 'Unknown')} (UUID: {svc.get('uuid', 'N/A')})")
            else:
                print("[!] No active services found. Device might be in non-discoverable mode.")
    except subprocess.TimeoutExpired:
        print("[!] Live GATT scan timed out. Device is likely not in pairing/discoverable mode.")
    except Exception as e:
        print(f"Discovery error: {e}")

def track_rssi(addr):
    """Real-time RSSI tracking loop with improved parsing."""
    print(f"\n[!] Starting Real-time RSSI Tracker for {addr}")
    print("[!] Tip: Move around to see signal changes.")
    print("[!] Press Ctrl+C to stop tracking.")
    
    # Use hcitool as a secondary source if btmgmt is slow
    try:
        while True:
            # Method 1: btmgmt find
            rssi_proc = subprocess.run(["sudo", "btmgmt", "find"], capture_output=True, text=True, timeout=3)
            found = False
            rssi_val = None
            
            for line in rssi_proc.stdout.splitlines():
                # Matching without case sensitivity and handling different formats
                if addr.upper() in line.upper() and "rssi" in line.lower():
                    try:
                        rssi_val = int(line.split('rssi')[-1].split()[0])
                        found = True
                        break
                    except:
                        continue
            
            if found and rssi_val is not None:
                bar_len = max(0, min(50, (rssi_val + 110) // 2))
                bar = "█" * bar_len + "-" * (50 - bar_len)
                print(f"\rRSSI: {rssi_val} dBm |{bar}|", end="", flush=True)
            else:
                # Method 2 fallback: passive hcitool scan if btmgmt is missing it
                print(f"\r[!] {addr} Searching...                      ", end="", flush=True)
            
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[!] RSSI Tracking stopped.")

def get_target_address():
    target_address = input("\nWhat is the target address? Leave blank and we will scan for you: ")

    if target_address == "":
        devices = scan_for_devices()
        if devices:
            # Show list of scanned devices for user selection
            while True:
                # Separate named from unknown for display consistency
                named_devices = [d for d in devices if not d[1].startswith("[Unknown Device]")]
                unknown_devices = [d for d in devices if d[1].startswith("[Unknown Device]")]
                
                print("\nDiscovered Devices:")
                for idx, (addr, name) in enumerate(named_devices):
                    print(f"{idx + 1}: Name: {name} | Address: {addr}")
                
                other_idx = len(named_devices) + 1
                if unknown_devices:
                    print(f"{other_idx}: -- Show Unknown Devices ({len(unknown_devices)} items) --")
                
                try:
                    selection_input = input("\nSelect a device by number (or Enter to exit): ").strip()
                    if not selection_input:
                        print("\nNo selection made. Exiting.")
                        return
                    
                    selection = int(selection_input) - 1
                    
                    chosen_device = None
                    if 0 <= selection < len(named_devices):
                        chosen_device = named_devices[selection]
                    elif selection == len(named_devices) and unknown_devices:
                        print("\nUnknown Devices:")
                        for idx, (addr, name) in enumerate(unknown_devices):
                            print(f"{idx + 1}: Name: {name} | Address: {addr}")
                        sub_choice = input(f"\nSelect an unknown device (1-{len(unknown_devices)}): ").strip()
                        if sub_choice.isdigit():
                            s_idx = int(sub_choice) - 1
                            if 0 <= s_idx < len(unknown_devices):
                                chosen_device = unknown_devices[s_idx]
                    
                    if chosen_device:
                        # Normalize MAC address format (strip RSSI if it was appended to UI name)
                        addr = chosen_device[0]
                        name = chosen_device[1]
                        
                        print(f"\nTarget Selected: {name}")
                        print(f"Address: {addr}")
                        print("-" * 20)
                        print("1: Attack (Deliver Payload)")
                        print("2: Discover Services (Scan UUIDs/GATT)")
                        print("3: Proximity Tracker (Real-time RSSI)")
                        print("4: Back to List")
                        
                        action = input("\nSelect action (1-4): ").strip()
                        if action == "1":
                            return addr
                        elif action == "2":
                            get_services(addr)
                            input("\nPress Enter to return to device list...")
                            continue 
                        elif action == "3":
                            track_rssi(addr)
                            input("\nPress Enter to return to device list...")
                            continue
                        else:
                            continue 
                    else:
                        print("\nInvalid selection. Try again.")
                        continue
                except ValueError:
                    print("\nInvalid input. Please enter a number.")
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

        # 3. RSSI Background Check
        print("Gathering signal strength (RSSI)...")
        device_rssi = {} # {addr: rssi}
        try:
            rssi_proc = subprocess.run(["sudo", "btmgmt", "find"], capture_output=True, text=True, timeout=2)
            for line in rssi_proc.stdout.splitlines():
                if "rssi" in line.lower():
                    # Parse line like: dev_found: 00:11:22:33:44:55 type BR/EDR rssi -60 ...
                    parts = line.split()
                    addr = next((p for p in parts if is_valid_mac_address(p)), None)
                    if addr:
                        rssi_val = line.split('rssi')[-1].split()[0]
                        device_rssi[addr.upper()] = rssi_val
        except:
            pass

        # 4. Finalize list with Names, OUI guesses, and RSSI
        print(f"Finalizing {len(unique_devices)} unique devices...")
        device_list = []
        for addr, name in unique_devices.items():
            final_name = name
            
            if not final_name:
                resolved = resolve_name(addr)
                if resolved: final_name = resolved
            
            display_name = final_name if final_name else f"[{get_vendor(addr)}]"
            
            # Add RSSI to display name if found
            rssi = device_rssi.get(addr.upper())
            if rssi:
                display_name = f"{display_name} [RSSI: {rssi}]"
                
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
