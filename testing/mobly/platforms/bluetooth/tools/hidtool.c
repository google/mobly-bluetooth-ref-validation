#include <hidapi/hidapi.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

#define SEND_SIZE 65
#define RECV_SIZE 129

#define VID 0x0416
#define PID 0xc145

#define TIMEOUT 10000

int main(int argc, char *argv[]) {
  if (argc <= 1) {
    printf("Requires argument `command`.");
    return 1;
  }

  unsigned char send_buf[SEND_SIZE];
  memset(send_buf, 0, SEND_SIZE);
  strcpy(send_buf + 1, argv[1]);

  printf("++hidapi test %s\n\r", __DATE__);
  int res = hid_init();
  printf("hid_init result = %d\n\r", res);

  struct hid_device_info *devs = hid_enumerate(VID, PID);
  struct hid_device_info *temp = devs;
  int failed_count = 0;
  while (temp) {
    printf("===================================\n\r");
    printf("Open HID device:\n\r");
    printf("  Path = %s\n\r", temp->path);
    printf("  Manufacturer String: %ls\n\r", temp->manufacturer_string);
    printf("  Product String: %ls\n\r", temp->product_string);
    printf("  Serial Number: %ls\n\r", temp->serial_number);

    hid_device *handle = hid_open_path(temp->path);
    if (!handle) {
      printf("Unable to open device (%s %s)\n\r", __TIME__, __DATE__);
      failed_count++;
      temp = temp->next;
      continue;
    }

    printf("start writing and reading\n\r");
    printf("Write cmd = %s\n", &send_buf[1]);
    int res = hid_write(handle, send_buf, SEND_SIZE);
    if (res == -1) {
      printf("HID write failed. Error: %ls\r\n", hid_error(handle));
      failed_count++;
      temp = temp->next;
      continue;
    }
    printf("HID write length = %d\n\r", res);

    unsigned char recv_buf[RECV_SIZE];
    memset(recv_buf, 0, RECV_SIZE);
    res = hid_read_timeout(handle, recv_buf, RECV_SIZE, TIMEOUT);
    if (res == -1) {
      printf("HID read failed. Error: %ls\r\n", hid_error(handle));
      failed_count++;
      temp = temp->next;
      continue;
    }
    printf("HID read length: %d, data: %s\n\r", res, recv_buf + 1);

    hid_close(handle);
    temp = temp->next;
  }

  hid_free_enumeration(devs);
  hid_exit();

  if (failed_count > 0) return 1;
  return 0;
}