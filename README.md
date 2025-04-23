# How to Run Mobly Bluetooth Reference Validation Tests

This doc describes how to run this validation suite.

## Implement the Mobly Controller of Bluetooth Reference Device

Implement a Mobly controller class in `testing/mobly/platforms/bluetooth` to
control your development board for Bluetooth testing. The Mobly controller
should inherit from 
`bluetooth_reference_device_base.BluetoothReferenceDeviceBase` and implement
all APIs in this base class.

`testing/mobly/platforms/bluetooth/example_device.py` provides an example
Mobly contoller for you to start with.

Import your newly created Mobly controller class in
`testing/mobly/platforms/bluetooth/bluetooth_reference_device.py`. And add the
class name in `SUPPORTED_DEVICE_CLASSES` list in this file for Mobly to
locate and instantiate the controller class in the test. 

## Prepare Devices

### Prepare Android Phone

1.  Prepare *two* Android phones.

1.  Log in your Google account (requires a VPN if needed) on the Android device.

1.  Enable
    [`developer options`](https://developer.android.com/studio/debug/dev-options#enable)
    on the Android device.

1.  Go to `Settings > System > Developer options`. Set `Disable Bluetooth LE
    audio` to **OFF**, and `Bypass Bluetooth LE Audio Allowlist` to **ON**.

1.  Go to `Settings > Google > Devices&sharing > Devices`. Set both
    `Scan for nearby devices` and `Include debug results` to **ON**.

1.  Connect the Android device to your PC/workstation. You will be running the
    Mobly test from this PC/workstation (the **host machine**).

    Ensure you can use [ADB](https://developer.android.com/tools/adb) to connect
    to this Android device by running this command on the host machine.

    ```bash
    adb devices
    ```

    You should see your Android device in the list.

    Take down the serial numbers of your Android devices. We'll need them in the
    following steps.

##  Prepare Test suite and configs

1. Modify Mobly device config YAML files under `config/` folder:
   `OneAndroidOneRefTestbed.yaml`, `OneAndroidTwoRefTestbed.yaml`,
   and `TwoAndroidOneRefTestbed.yaml`.

    + Configure the Android device serials in `TwoAndroidOneRefTestbed.yaml`.
      Specify the serial number of the Android device like this:

      ```yaml
      TestBeds:
      - Name: LocalTestbed
        Controllers:
          AndroidDevice:
            - serial: '0000000000000A'
            - serial: '0000000000000B'
      ```

    + Configure the Bluetooth reference device in each file. Fill the
    `controller_name` field with a newly added Mobly class name.

      ```yaml
      TestBeds:
      - Name: LocalTestbed
        Controllers:
          AndroidDevice:
            - serial: '0000000000000A'
            - serial: '0000000000000B'
          BluetoothReferenceDevice:
          - controller_name: BtBoardDevice
            serial_port: '/dev/ttyUSB0'
            bluetooth_address: '11:22:33:44:55:66'
      ```

1.  If you are running on a **Windows** PC, add a `LogPath` field to
    `MoblyParams`:

    ```yaml
    TestBeds:
    - Name: LocalTestbed
      Controllers:
        AndroidDevice:
          - serial: '0000000000000A'
          - serial: '0000000000000B'
        BluetoothReferenceDevice:
          - controller_name: BtBoardDevice
            serial_port: '/dev/ttyUSB0'
            bluetooth_address: '11:22:33:44:55:66'
    MoblyParams:
      LogPath: 'C:\User\<username>\AppData\Local\Temp'
    ```

1.  Save the configure YAML file.

## Run the Mobly Test

Now you are able to run the example Mobly tests.

1.  Create a new python virtual environment to run the test or activte an existing
    virtual environment.

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

1.  Install the python dependencies on the **host machine**(your PC/workstation).

    ```bash
    pip3 install -r requirements.txt
    ```

1.  Quick test if the environment is correctly set up and is able to run this
    test suite:

    ```bash
    python3 testing/bt_pair_test.py -c config/OneAndroidOneRefTestbed.yaml
    ```

1.  Run all three Mobly test suites.

    ```bash
    python3 one_android_one_ref_suite.py -c config/OneAndroidOneRefTestbed.yaml
    ```

    ```bash
    python3 one_android_two_ref_suite.py -c config/OneAndroidTwoRefTestbed.yaml
    ```

    ```bash
    python3 two_android_one_ref_suite.py -c config/TwoAndroidOneRefTestbed.yaml
    ```

1.  Ensure the test result of the above three test suites are all passed with
    0 error, 0 failed, and 0 skipped.
