#define BOOTSTUB

#define VERS_TAG 0x53524556
#define MIN_VERSION 2

#include "config.h"

#include "drivers/pwm.h"
#include "drivers/usb.h"

#include "early_init.h"
#include "provision.h"

#include "crypto/rsa.h"
#include "crypto/sha.h"

#include "obj/cert.h"
#include "obj/gitversion.h"
#include "flasher.h"

void __initialize_hardware_early(void) {
  early_initialization();
}

void fail(void) {
  soft_flasher_start();
}

extern void *_app_start[];

int main(void) {

  init_interrupts(true);

  disable_interrupts();
  clock_init();
  detect_external_debug_serial();
  detect_board_type();

  if (enter_bootloader_mode == ENTER_SOFTLOADER_MAGIC) {
    enter_bootloader_mode = 0;
    soft_flasher_start();
  }

  int len = (int)_app_start[0];
  if ((len < 8) || (len > (0x1000000 - 0x4000 - 4 - RSANUMBYTES))) goto fail;

  uint8_t digest[SHA_DIGEST_SIZE];
  SHA_hash(&_app_start[1], len-4, digest);

  uint32_t vers[2] = {0};
  memcpy(&vers, ((void*)&_app_start[0]) + len - sizeof(vers), sizeof(vers));
  if (vers[0] != VERS_TAG || vers[1] < MIN_VERSION) {
    goto fail;
  }

  if (RSA_verify(&release_rsa_key, ((void*)&_app_start[0]) + len, RSANUMBYTES, digest, SHA_DIGEST_SIZE)) {
    goto good;
  }

#ifdef ALLOW_DEBUG
  if (RSA_verify(&debug_rsa_key, ((void*)&_app_start[0]) + len, RSANUMBYTES, digest, SHA_DIGEST_SIZE)) {
    goto good;
  }
#endif

fail:
  fail();
  return 0;
good:

  ((void(*)(void)) _app_start[1])();
  return 0;
}
