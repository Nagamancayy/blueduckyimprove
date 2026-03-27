# BlueDucky-Improve 🦆🚀

Improved version of BlueDucky (CVE-2023-45866) by Nagamancayy. Specifically refactored for better compatibility with CSR 4.0 dongles and virtualized environments (UTM/Kali).

## New Features
- **Mode Selection**: Choose between **Normal** (Standard attack) and **Annoy** (Persistent pairing spam).
- **Improved Compatibility**: Removed problematic hardware renaming logic (`set_property`) that caused hangs and failures on many USB adapters.
- **Auto-Retry**: Annoy mode automatically retries connection if the target rejects the pairing, creating a "Pop-up Bomb" effect via social engineering.

## Installation
Same as original, but optimized for Kali Linux on ARM64 (UTM).

```bash
git clone https://github.com/Nagamancayy/blueduckyimprove.git
cd blueduckyimprove
pip3 install -r requirements.txt
```

## Usage
1. Initialize your adapter: `sudo hciconfig hci0 up`
2. Run the script: `sudo python3 BlueDucky.py`
3. Follow the menu to select target and payload.
4. **Choose Mode**:
   - `1`: Normal mode (ideal for unpatched devices).
   - `2`: Annoy mode (perfect for social engineering on patched devices).

## Troubleshooting
If the script hangs on start, ensure you have commented out the `troubleshoot_bluetooth()` line in `BlueDucky.py`. This version has been pre-configured to skip problematic hardware checks for maximum stability.

---
*Disclaimer: For educational and authorized security testing purposes only.*
