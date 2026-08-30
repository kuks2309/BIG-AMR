
typedef union {
  uint16_t w;
  struct BW {
    uint8_t msb;
    uint8_t lsb;
  }
  bw;
}
uint16_t_uint8_t;

typedef union _USB_Setup {
  uint32_t d8[2];
  struct _SetupPkt_Struc
  {
    uint8_t           bmRequestType;
    uint8_t           bRequest;
    uint16_t_uint8_t  wValue;
    uint16_t_uint8_t  wIndex;
    uint16_t_uint8_t  wLength;
  } b;
}
USB_Setup_TypeDef;

bool usb_enumerated = false;

void usb_init(void);
int usb_cb_control_msg(USB_Setup_TypeDef *setup, uint8_t *resp);
int usb_cb_ep1_in(void *usbdata, int len);
void usb_cb_ep2_out(void *usbdata, int len);
void usb_cb_ep3_out(void *usbdata, int len);
void usb_cb_ep3_out_complete(void);
void usb_cb_enumeration_complete(void);
void usb_outep3_resume_if_paused(void);

#define  USB_REQ_GET_STATUS                             0x00
#define  USB_REQ_CLEAR_FEATURE                          0x01
#define  USB_REQ_SET_FEATURE                            0x03
#define  USB_REQ_SET_ADDRESS                            0x05
#define  USB_REQ_GET_DESCRIPTOR                         0x06
#define  USB_REQ_SET_DESCRIPTOR                         0x07
#define  USB_REQ_GET_CONFIGURATION                      0x08
#define  USB_REQ_SET_CONFIGURATION                      0x09
#define  USB_REQ_GET_INTERFACE                          0x0A
#define  USB_REQ_SET_INTERFACE                          0x0B
#define  USB_REQ_SYNCH_FRAME                            0x0C

#define  USB_DESC_TYPE_DEVICE                           0x01
#define  USB_DESC_TYPE_CONFIGURATION                    0x02
#define  USB_DESC_TYPE_STRING                           0x03
#define  USB_DESC_TYPE_INTERFACE                        0x04
#define  USB_DESC_TYPE_ENDPOINT                         0x05
#define  USB_DESC_TYPE_DEVICE_QUALIFIER                 0x06
#define  USB_DESC_TYPE_OTHER_SPEED_CONFIGURATION        0x07
#define  USB_DESC_TYPE_BINARY_OBJECT_STORE              0x0f

#define  STRING_OFFSET_LANGID                           0x00
#define  STRING_OFFSET_IMANUFACTURER                    0x01
#define  STRING_OFFSET_IPRODUCT                         0x02
#define  STRING_OFFSET_ISERIAL                          0x03
#define  STRING_OFFSET_ICONFIGURATION                   0x04
#define  STRING_OFFSET_IINTERFACE                       0x05

#define  WEBUSB_REQ_GET_URL                             0x02

#define  WEBUSB_DESC_TYPE_URL                           0x03
#define  WEBUSB_URL_SCHEME_HTTPS                        0x01
#define  WEBUSB_URL_SCHEME_HTTP                         0x00

#define  WINUSB_REQ_GET_COMPATID_DESCRIPTOR             0x04
#define  WINUSB_REQ_GET_EXT_PROPS_OS                    0x05
#define  WINUSB_REQ_GET_DESCRIPTOR                      0x07

#define STS_GOUT_NAK                           1
#define STS_DATA_UPDT                          2
#define STS_XFER_COMP                          3
#define STS_SETUP_COMP                         4
#define STS_SETUP_UPDT                         6

uint8_t resp[USBPACKET_MAX_SIZE];

#define DSCR_INTERFACE_LEN 9
#define DSCR_ENDPOINT_LEN 7
#define DSCR_CONFIG_LEN 9
#define DSCR_DEVICE_LEN 18

#define ENDPOINT_TYPE_CONTROL 0
#define ENDPOINT_TYPE_ISO 1
#define ENDPOINT_TYPE_BULK 2
#define ENDPOINT_TYPE_INT 3

#define  MS_VENDOR_CODE 0x20
#define  WEBUSB_VENDOR_CODE 0x30

#define BINARY_OBJECT_STORE_DESCRIPTOR_LENGTH   0x05
#define BINARY_OBJECT_STORE_DESCRIPTOR          0x0F
#define WINUSB_PLATFORM_DESCRIPTOR_LENGTH       0x9E

#define TOUSBORDER(num)\
  ((num) & 0xFFU), (((num) >> 8) & 0xFFU)

#define STRING_DESCRIPTOR_HEADER(size)\
  (((((size) * 2) + 2) & 0xFF) | 0x0300)

uint8_t device_desc[] = {
  DSCR_DEVICE_LEN, USB_DESC_TYPE_DEVICE,
  0x10, 0x02,
  0xFF, 0xFF, 0xFF, 0x40,
  TOUSBORDER(USB_VID),
  TOUSBORDER(USB_PID),
  0x00, 0x00,
  0x01, 0x02,
  0x03, 0x01
};

uint8_t device_qualifier[] = {
  0x0a, USB_DESC_TYPE_DEVICE_QUALIFIER,
  0x10, 0x02,
  0xFF, 0xFF, 0xFF, 0x40,
  0x01, 0x00
};

#define ENDPOINT_RCV 0x80
#define ENDPOINT_SND 0x00

uint8_t configuration_desc[] = {
  DSCR_CONFIG_LEN, USB_DESC_TYPE_CONFIGURATION,
  TOUSBORDER(0x0045U),
  0x01, 0x01, STRING_OFFSET_ICONFIGURATION,
  0xc0, 0x32,

  DSCR_INTERFACE_LEN, USB_DESC_TYPE_INTERFACE,
  0x00, 0x00, 0x03,
  0XFF, 0xFF, 0xFF,
  0x00,

    DSCR_ENDPOINT_LEN, USB_DESC_TYPE_ENDPOINT,
    ENDPOINT_RCV | 1, ENDPOINT_TYPE_BULK,
    TOUSBORDER(0x0040U),
    0x00,

    DSCR_ENDPOINT_LEN, USB_DESC_TYPE_ENDPOINT,
    ENDPOINT_SND | 2, ENDPOINT_TYPE_BULK,
    TOUSBORDER(0x0040U),
    0x00,

    DSCR_ENDPOINT_LEN, USB_DESC_TYPE_ENDPOINT,
    ENDPOINT_SND | 3, ENDPOINT_TYPE_BULK,
    TOUSBORDER(0x0040U),
    0x00,

  DSCR_INTERFACE_LEN, USB_DESC_TYPE_INTERFACE,
  0x00, 0x01, 0x03,
  0XFF, 0xFF, 0xFF,
  0x00,

    DSCR_ENDPOINT_LEN, USB_DESC_TYPE_ENDPOINT,
    ENDPOINT_RCV | 1, ENDPOINT_TYPE_INT,
    TOUSBORDER(0x0040U),
    0x05,

    DSCR_ENDPOINT_LEN, USB_DESC_TYPE_ENDPOINT,
    ENDPOINT_SND | 2, ENDPOINT_TYPE_BULK,
    TOUSBORDER(0x0040U),
    0x00,

    DSCR_ENDPOINT_LEN, USB_DESC_TYPE_ENDPOINT,
    ENDPOINT_SND | 3, ENDPOINT_TYPE_BULK,
    TOUSBORDER(0x0040U),
    0x00,
};

uint16_t string_language_desc[] = {
  STRING_DESCRIPTOR_HEADER(1),
  0x0409
};

uint16_t string_manufacturer_desc[] = {
  STRING_DESCRIPTOR_HEADER(8),
  'c', 'o', 'm', 'm', 'a', '.', 'a', 'i'
};

uint16_t string_product_desc[] = {
  STRING_DESCRIPTOR_HEADER(5),
  'p', 'a', 'n', 'd', 'a'
};

uint16_t string_serial_desc[] = {
  STRING_DESCRIPTOR_HEADER(4),
  'n', 'o', 'n', 'e'
};

uint16_t string_configuration_desc[] = {
  STRING_DESCRIPTOR_HEADER(2),
  '0', '1'
};

uint8_t string_238_desc[] = {
  0x12, USB_DESC_TYPE_STRING,
  'M',0, 'S',0, 'F',0, 'T',0, '1',0, '0',0, '0',0,
  MS_VENDOR_CODE, 0x00
};
uint8_t winusb_ext_compatid_os_desc[] = {
  0x28, 0x00, 0x00, 0x00,
  0x00, 0x01,
  0x04, 0x00,
  0x01,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00,
  0x00,
  'W', 'I', 'N', 'U', 'S', 'B', 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};
uint8_t winusb_ext_prop_os_desc[] = {
  0x8e, 0x00, 0x00, 0x00,
  0x00, 0x01,
  0x05, 0x00,
  0x01, 0x00,

  0x84, 0x00, 0x00, 0x00,
  0x01, 0x00, 0x00, 0x00,
  0x28, 0x00,
  'D',0, 'e',0, 'v',0, 'i',0, 'c',0, 'e',0, 'I',0, 'n',0, 't',0, 'e',0, 'r',0, 'f',0, 'a',0, 'c',0, 'e',0, 'G',0, 'U',0, 'I',0, 'D',0, 0, 0,
  0x4e, 0x00, 0x00, 0x00,
  '{',0, 'c',0, 'c',0, 'e',0, '5',0, '2',0, '9',0, '1',0, 'c',0, '-',0, 'a',0, '6',0, '9',0, 'f',0, '-',0, '4',0 ,'9',0 ,'9',0 ,'5',0 ,'-',0, 'a',0, '4',0, 'c',0, '2',0, '-',0, '2',0, 'a',0, 'e',0, '5',0, '7',0, 'a',0, '5',0, '1',0, 'a',0, 'd',0, 'e',0, '9',0, '}',0, 0, 0,
};

uint8_t binary_object_store_desc[] = {

  BINARY_OBJECT_STORE_DESCRIPTOR_LENGTH,
  BINARY_OBJECT_STORE_DESCRIPTOR,
  0x39, 0x00,
  0x02,

    0x18,
    0x10,
    0x05,
    0x00,

    0x38, 0xB6, 0x08, 0x34,
    0xA9, 0x09, 0xA0, 0x47,
    0x8B, 0xFD, 0xA0, 0x76,
    0x88, 0x15, 0xB6, 0x65,

  0x00, 0x01,
  WEBUSB_VENDOR_CODE,

  0x03,

    0x1C,
    0x10,
    0x05,
    0x00,

    0xDF, 0x60, 0xDD, 0xD8,
    0x89, 0x45, 0xC7, 0x4C,
    0x9C, 0xD2, 0x65, 0x9D,
    0x9E, 0x64, 0x8A, 0x9F,

  0x00, 0x00, 0x03, 0x06,

  WINUSB_PLATFORM_DESCRIPTOR_LENGTH, 0x00,
  MS_VENDOR_CODE, 0x00
};

uint8_t webusb_url_descriptor[] = {
  0x14,
  WEBUSB_DESC_TYPE_URL,
  WEBUSB_URL_SCHEME_HTTPS,
  'u', 's', 'b', 'p', 'a', 'n', 'd', 'a', '.', 'c', 'o', 'm', 'm', 'a', '.', 'a', 'i'
};

uint8_t winusb_20_desc[WINUSB_PLATFORM_DESCRIPTOR_LENGTH] = {

  0x0A, 0x00,
  0x00, 0x00,

  0x00, 0x00, 0x03, 0x06,
  WINUSB_PLATFORM_DESCRIPTOR_LENGTH, 0x00,

    0x14, 0x00,
    0x03, 0x00,
    'W', 'I', 'N', 'U', 'S', 'B', 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,

  0x80, 0x00,
  0x04, 0x00,
  0x01, 0x00,
  0x28, 0x00,

    'D', 0x00, 'e', 0x00, 'v', 0x00, 'i', 0x00, 'c', 0x00, 'e', 0x00, 'I', 0x00, 'n', 0x00,
    't', 0x00, 'e', 0x00, 'r', 0x00, 'f', 0x00, 'a', 0x00, 'c', 0x00, 'e', 0x00, 'G', 0x00,
    'U', 0x00, 'I', 0x00, 'D', 0x00, 0x00, 0x00,

  0x4E, 0x00,

    '{', 0x00, 'c', 0x00, 'c', 0x00, 'e', 0x00, '5', 0x00, '2', 0x00, '9', 0x00, '1', 0x00,
    'c', 0x00, '-', 0x00, 'a', 0x00, '6', 0x00, '9', 0x00, 'f', 0x00, '-', 0x00, '4', 0x00,
    '9', 0x00, '9', 0x00, '5', 0x00, '-', 0x00, 'a', 0x00, '4', 0x00, 'c', 0x00, '2', 0x00,
    '-', 0x00, '2', 0x00, 'a', 0x00, 'e', 0x00, '5', 0x00, '7', 0x00, 'a', 0x00, '5', 0x00,
    '1', 0x00, 'a', 0x00, 'd', 0x00, 'e', 0x00, '9', 0x00, '}', 0x00, 0x00, 0x00
};

USB_Setup_TypeDef setup;
uint8_t usbdata[0x100];
uint8_t* ep0_txdata = NULL;
uint16_t ep0_txlen = 0;
bool outep3_processing = false;

int current_int0_alt_setting = 0;

void *USB_ReadPacket(void *dest, uint16_t len) {
  uint32_t *dest_copy = (uint32_t *)dest;
  uint32_t count32b = (len + 3U) / 4U;

  for (uint32_t i = 0; i < count32b; i++) {
    *dest_copy = USBx_DFIFO(0);
    dest_copy++;
  }
  return ((void *)dest_copy);
}

void USB_WritePacket(const void *src, uint16_t len, uint32_t ep) {
  #ifdef DEBUG_USB
  puts("writing ");
  hexdump(src, len);
  #endif

  uint32_t numpacket = (len + (USBPACKET_MAX_SIZE - 1U)) / USBPACKET_MAX_SIZE;
  uint32_t count32b = 0;
  count32b = (len + 3U) / 4U;

  USBx_INEP(ep)->DIEPTSIZ = ((numpacket << 19) & USB_OTG_DIEPTSIZ_PKTCNT) |
                            (len               & USB_OTG_DIEPTSIZ_XFRSIZ);
  USBx_INEP(ep)->DIEPCTL |= (USB_OTG_DIEPCTL_CNAK | USB_OTG_DIEPCTL_EPENA);

  if (src != NULL) {
    const uint32_t *src_copy = (const uint32_t *)src;
    for (uint32_t i = 0; i < count32b; i++) {
      USBx_DFIFO(ep) = *src_copy;
      src_copy++;
    }
  }
}

void USB_WritePacket_EP0(uint8_t *src, uint16_t len) {
  #ifdef DEBUG_USB
  puts("writing ");
  hexdump(src, len);
  #endif

  uint16_t wplen = MIN(len, 0x40);
  USB_WritePacket(src, wplen, 0);

  if (wplen < len) {
    ep0_txdata = &src[wplen];
    ep0_txlen = len - wplen;
    USBx_DEVICE->DIEPEMPMSK |= 1;
  } else {
    USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
  }
}

void usb_reset(void) {

  USBx_DEVICE->DAINT = 0xFFFFFFFF;
  USBx_DEVICE->DAINTMSK = 0xFFFFFFFF;

  USBx_DEVICE->DIEPMSK = 0xFFFFFFFF;
  USBx_DEVICE->DOEPMSK = 0xFFFFFFFF;

  USBx_INEP(0)->DIEPINT = 0xFF;
  USBx_OUTEP(0)->DOEPINT = 0xFF;

  USBx_DEVICE->DCFG &= ~USB_OTG_DCFG_DAD;

  USBx->GRXFSIZ = 0x40;

  USBx->DIEPTXF0_HNPTXFSIZ = (0x40U << 16) | 0x40U;

  USBx->DIEPTXF[0] = (0x40U << 16) | 0x80U;

  USBx->GRSTCTL = USB_OTG_GRSTCTL_TXFFLSH | USB_OTG_GRSTCTL_TXFNUM_4;
  while ((USBx->GRSTCTL & USB_OTG_GRSTCTL_TXFFLSH) == USB_OTG_GRSTCTL_TXFFLSH);

  USBx->GRSTCTL = USB_OTG_GRSTCTL_RXFFLSH;
  while ((USBx->GRSTCTL & USB_OTG_GRSTCTL_RXFFLSH) == USB_OTG_GRSTCTL_RXFFLSH);

  USBx_DEVICE->DCTL |= USB_OTG_DCTL_CGINAK;

  USBx_OUTEP(0)->DOEPTSIZ = USB_OTG_DOEPTSIZ_STUPCNT | (USB_OTG_DOEPTSIZ_PKTCNT & (1U << 19)) | (3U << 3);
}

char to_hex_char(int a) {
  char ret;
  if (a < 10) {
    ret = '0' + a;
  } else {
    ret = 'a' + (a - 10);
  }
  return ret;
}

void usb_setup(void) {
  int resp_len;

  switch (setup.b.bRequest) {
    case USB_REQ_SET_CONFIGURATION:

      USBx_INEP(1)->DIEPCTL = (0x40U & USB_OTG_DIEPCTL_MPSIZ) | (2U << 18) | (1U << 22) |
                              USB_OTG_DIEPCTL_SD0PID_SEVNFRM | USB_OTG_DIEPCTL_USBAEP;
      USBx_INEP(1)->DIEPINT = 0xFF;

      USBx_OUTEP(2)->DOEPTSIZ = (1U << 19) | 0x40U;
      USBx_OUTEP(2)->DOEPCTL = (0x40U & USB_OTG_DOEPCTL_MPSIZ) | (2U << 18) |
                               USB_OTG_DOEPCTL_SD0PID_SEVNFRM | USB_OTG_DOEPCTL_USBAEP;
      USBx_OUTEP(2)->DOEPINT = 0xFF;

      USBx_OUTEP(3)->DOEPTSIZ = (32U << 19) | 0x800U;
      USBx_OUTEP(3)->DOEPCTL = (0x40U & USB_OTG_DOEPCTL_MPSIZ) | (2U << 18) |
                               USB_OTG_DOEPCTL_SD0PID_SEVNFRM | USB_OTG_DOEPCTL_USBAEP;
      USBx_OUTEP(3)->DOEPINT = 0xFF;

      USBx_OUTEP(2)->DOEPCTL |= USB_OTG_DOEPCTL_EPENA | USB_OTG_DOEPCTL_CNAK;
      USBx_OUTEP(3)->DOEPCTL |= USB_OTG_DOEPCTL_EPENA | USB_OTG_DOEPCTL_CNAK;

      USB_WritePacket(0, 0, 0);
      USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
      break;
    case USB_REQ_SET_ADDRESS:

      USBx_DEVICE->DCFG |= ((setup.b.wValue.w & 0x7fU) << 4);

      #ifdef DEBUG_USB
        puts(" set address\n");
      #endif

      usb_cb_enumeration_complete();

      USB_WritePacket(0, 0, 0);
      USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;

      break;
    case USB_REQ_GET_DESCRIPTOR:
      switch (setup.b.wValue.bw.lsb) {
        case USB_DESC_TYPE_DEVICE:

          device_desc[13] = hw_type;

          USB_WritePacket(device_desc, MIN(sizeof(device_desc), setup.b.wLength.w), 0);
          USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;

          break;
        case USB_DESC_TYPE_CONFIGURATION:
          USB_WritePacket(configuration_desc, MIN(sizeof(configuration_desc), setup.b.wLength.w), 0);
          USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
          break;
        case USB_DESC_TYPE_DEVICE_QUALIFIER:
          USB_WritePacket(device_qualifier, MIN(sizeof(device_qualifier), setup.b.wLength.w), 0);
          USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
          break;
        case USB_DESC_TYPE_STRING:
          switch (setup.b.wValue.bw.msb) {
            case STRING_OFFSET_LANGID:
              USB_WritePacket((uint8_t*)string_language_desc, MIN(sizeof(string_language_desc), setup.b.wLength.w), 0);
              break;
            case STRING_OFFSET_IMANUFACTURER:
              USB_WritePacket((uint8_t*)string_manufacturer_desc, MIN(sizeof(string_manufacturer_desc), setup.b.wLength.w), 0);
              break;
            case STRING_OFFSET_IPRODUCT:
              USB_WritePacket((uint8_t*)string_product_desc, MIN(sizeof(string_product_desc), setup.b.wLength.w), 0);
              break;
            case STRING_OFFSET_ISERIAL:
              #ifdef UID_BASE
                resp[0] = 0x02 + (12 * 4);
                resp[1] = 0x03;

                for (int i = 0; i < 12; i++){
                  uint8_t cc = ((uint8_t *)UID_BASE)[i];
                  resp[2 + (i * 4) + 0] = to_hex_char((cc >> 4) & 0xFU);
                  resp[2 + (i * 4) + 1] = '\0';
                  resp[2 + (i * 4) + 2] = to_hex_char((cc >> 0) & 0xFU);
                  resp[2 + (i * 4) + 3] = '\0';
                }

                USB_WritePacket(resp, MIN(resp[0], setup.b.wLength.w), 0);
              #else
                USB_WritePacket((const uint8_t *)string_serial_desc, MIN(sizeof(string_serial_desc), setup.b.wLength.w), 0);
              #endif
              break;
            case STRING_OFFSET_ICONFIGURATION:
              USB_WritePacket((uint8_t*)string_configuration_desc, MIN(sizeof(string_configuration_desc), setup.b.wLength.w), 0);
              break;
            case 238:
              USB_WritePacket((uint8_t*)string_238_desc, MIN(sizeof(string_238_desc), setup.b.wLength.w), 0);
              break;
            default:

              USB_WritePacket(0, 0, 0);
              break;
          }
          USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
          break;
        case USB_DESC_TYPE_BINARY_OBJECT_STORE:
          USB_WritePacket(binary_object_store_desc, MIN(sizeof(binary_object_store_desc), setup.b.wLength.w), 0);
          USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
          break;
        default:

          USB_WritePacket(0, 0, 0);
          USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
          break;
      }
      break;
    case USB_REQ_GET_STATUS:

      resp[0] = 0;
      resp[1] = 0;
      USB_WritePacket((void*)&resp, 2, 0);
      USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
      break;
    case USB_REQ_SET_INTERFACE:

      current_int0_alt_setting = setup.b.wValue.w;
      USB_WritePacket(0, 0, 0);
      USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
      break;
    case WEBUSB_VENDOR_CODE:
      switch (setup.b.wIndex.w) {
        case WEBUSB_REQ_GET_URL:
          USB_WritePacket(webusb_url_descriptor, MIN(sizeof(webusb_url_descriptor), setup.b.wLength.w), 0);
          USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
          break;
        default:

          USB_WritePacket(0, 0, 0);
          USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
          break;
      }
      break;
    case MS_VENDOR_CODE:
      switch (setup.b.wIndex.w) {

        case WINUSB_REQ_GET_DESCRIPTOR:
          USB_WritePacket_EP0((uint8_t*)winusb_20_desc, MIN(sizeof(winusb_20_desc), setup.b.wLength.w));
          break;

        case WINUSB_REQ_GET_COMPATID_DESCRIPTOR:
          USB_WritePacket_EP0((uint8_t*)winusb_ext_compatid_os_desc, MIN(sizeof(winusb_ext_compatid_os_desc), setup.b.wLength.w));
          break;

        case WINUSB_REQ_GET_EXT_PROPS_OS:
          USB_WritePacket_EP0((uint8_t*)winusb_ext_prop_os_desc, MIN(sizeof(winusb_ext_prop_os_desc), setup.b.wLength.w));
          break;
        default:
          USB_WritePacket_EP0(0, 0);
      }
      break;
    default:
      resp_len = usb_cb_control_msg(&setup, resp);

      if (resp_len != -1) {
        USB_WritePacket(resp, MIN(resp_len, setup.b.wLength.w), 0);
        USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
      }
  }
}

void usb_irqhandler(void) {

  unsigned int gintsts = USBx->GINTSTS;
  unsigned int gotgint = USBx->GOTGINT;
  unsigned int daint = USBx_DEVICE->DAINT;

  #ifdef DEBUG_USB
    puth(gintsts);
    puts(" ");

    puth(gotgint);
    puts(" ep ");
    puth(daint);
    puts(" USB interrupt!\n");
  #endif

  if ((gintsts & USB_OTG_GINTSTS_CIDSCHG) != 0) {
    puts("connector ID status change\n");
  }

  if ((gintsts & USB_OTG_GINTSTS_ESUSP) != 0) {
    puts("ESUSP detected\n");
  }

  if ((gintsts & USB_OTG_GINTSTS_EOPF) != 0) {
    usb_enumerated = true;
  }

  if ((gintsts & USB_OTG_GINTSTS_USBRST) != 0) {
    puts("USB reset\n");
    usb_enumerated = false;
    usb_reset();
  }

  if ((gintsts & USB_OTG_GINTSTS_USBSUSP) != 0) {
    usb_enumerated = false;
  }

  if ((gintsts & USB_OTG_GINTSTS_ENUMDNE) != 0) {
    puts("enumeration done");

    puts("\n");
  }

  if ((gintsts & USB_OTG_GINTSTS_OTGINT) != 0) {
    puts("OTG int:");
    puth(USBx->GOTGINT);
    puts("\n");

  }

  if ((gintsts & USB_OTG_GINTSTS_RXFLVL) != 0) {

    volatile unsigned int rxst = USBx->GRXSTSP;
    int status = (rxst & USB_OTG_GRXSTSP_PKTSTS) >> 17;

    #ifdef DEBUG_USB
      puts(" RX FIFO:");
      puth(rxst);
      puts(" status: ");
      puth(status);
      puts(" len: ");
      puth((rxst & USB_OTG_GRXSTSP_BCNT) >> 4);
      puts("\n");
    #endif

    if (status == STS_DATA_UPDT) {
      int endpoint = (rxst & USB_OTG_GRXSTSP_EPNUM);
      int len = (rxst & USB_OTG_GRXSTSP_BCNT) >> 4;
      (void)USB_ReadPacket(&usbdata, len);
      #ifdef DEBUG_USB
        puts("  data ");
        puth(len);
        puts("\n");
        hexdump(&usbdata, len);
      #endif

      if (endpoint == 2) {
        usb_cb_ep2_out(usbdata, len);
      }

      if (endpoint == 3) {
        outep3_processing = true;
        usb_cb_ep3_out(usbdata, len);
      }
    } else if (status == STS_SETUP_UPDT) {
      (void)USB_ReadPacket(&setup, 8);
      #ifdef DEBUG_USB
        puts("  setup ");
        hexdump(&setup, 8);
        puts("\n");
      #endif
    } else {

    }
  }

  if ((gintsts & USB_OTG_GINTSTS_BOUTNAKEFF) || (gintsts & USB_OTG_GINTSTS_GINAKEFF)) {

    #ifdef DEBUG_USB
      puts("GLOBAL NAK\n");
    #endif
    USBx_DEVICE->DCTL |= USB_OTG_DCTL_CGONAK | USB_OTG_DCTL_CGINAK;
  }

  if ((gintsts & USB_OTG_GINTSTS_SRQINT) != 0) {

  }

  if ((gintsts & USB_OTG_GINTSTS_OEPINT) != 0) {
    #ifdef DEBUG_USB
      puts("  0:");
      puth(USBx_OUTEP(0)->DOEPINT);
      puts(" 2:");
      puth(USBx_OUTEP(2)->DOEPINT);
      puts(" 3:");
      puth(USBx_OUTEP(3)->DOEPINT);
      puts(" ");
      puth(USBx_OUTEP(3)->DOEPCTL);
      puts(" 4:");
      puth(USBx_OUTEP(4)->DOEPINT);
      puts(" OUT ENDPOINT\n");
    #endif

    if ((USBx_OUTEP(2)->DOEPINT & USB_OTG_DOEPINT_XFRC) != 0) {
      #ifdef DEBUG_USB
        puts("  OUT2 PACKET XFRC\n");
      #endif
      USBx_OUTEP(2)->DOEPTSIZ = (1U << 19) | 0x40U;
      USBx_OUTEP(2)->DOEPCTL |= USB_OTG_DOEPCTL_EPENA | USB_OTG_DOEPCTL_CNAK;
    }

    if ((USBx_OUTEP(3)->DOEPINT & USB_OTG_DOEPINT_XFRC) != 0) {
      #ifdef DEBUG_USB
        puts("  OUT3 PACKET XFRC\n");
      #endif

      outep3_processing = false;
      usb_cb_ep3_out_complete();
    } else if ((USBx_OUTEP(3)->DOEPINT & 0x2000) != 0) {
      #ifdef DEBUG_USB
        puts("  OUT3 PACKET WTF\n");
      #endif

    } else if ((USBx_OUTEP(3)->DOEPINT) != 0) {
      #ifdef DEBUG_USB
        puts("OUTEP3 error ");
        puth(USBx_OUTEP(3)->DOEPINT);
        puts("\n");
      #endif
    } else {

    }

    if ((USBx_OUTEP(0)->DOEPINT & USB_OTG_DIEPINT_XFRC) != 0) {

      USBx_OUTEP(0)->DOEPTSIZ = USB_OTG_DOEPTSIZ_STUPCNT | (USB_OTG_DOEPTSIZ_PKTCNT & (1U << 19)) | (1U << 3);
    }

    if ((USBx_OUTEP(0)->DOEPINT & USB_OTG_DOEPINT_STUP) != 0) {
      usb_setup();
    }

    USBx_OUTEP(0)->DOEPINT = USBx_OUTEP(0)->DOEPINT;
    USBx_OUTEP(2)->DOEPINT = USBx_OUTEP(2)->DOEPINT;
    USBx_OUTEP(3)->DOEPINT = USBx_OUTEP(3)->DOEPINT;
  }

  if ((gintsts & USB_OTG_GINTSTS_IEPINT) != 0) {
    #ifdef DEBUG_USB
      puts("  ");
      puth(USBx_INEP(0)->DIEPINT);
      puts(" ");
      puth(USBx_INEP(1)->DIEPINT);
      puts(" IN ENDPOINT\n");
    #endif

    switch (current_int0_alt_setting) {
      case 0:

        if ((USBx_INEP(1)->DIEPINT & USB_OTG_DIEPMSK_ITTXFEMSK) != 0) {
          #ifdef DEBUG_USB
          puts("  IN PACKET QUEUE\n");
          #endif

          USB_WritePacket((void *)resp, usb_cb_ep1_in(resp, 0x40), 1);
        }
        break;

      case 1:

        if ((USBx_INEP(1)->DIEPINT & USB_OTG_DIEPMSK_ITTXFEMSK) != 0) {
          #ifdef DEBUG_USB
          puts("  IN PACKET QUEUE\n");
          #endif

          int len = usb_cb_ep1_in(resp, 0x40);
          if (len > 0) {
            USB_WritePacket((void *)resp, len, 1);
          }
        }
        break;
      default:
        puts("current_int0_alt_setting value invalid\n");
        break;
    }

    if ((USBx_INEP(0)->DIEPINT & USB_OTG_DIEPMSK_ITTXFEMSK) != 0) {
      #ifdef DEBUG_USB
      puts("  IN PACKET QUEUE\n");
      #endif

      if ((ep0_txlen != 0U) && ((USBx_INEP(0)->DTXFSTS & USB_OTG_DTXFSTS_INEPTFSAV) >= 0x40U)) {
        uint16_t len = MIN(ep0_txlen, 0x40);
        USB_WritePacket(ep0_txdata, len, 0);
        ep0_txdata = &ep0_txdata[len];
        ep0_txlen -= len;
        if (ep0_txlen == 0U) {
          ep0_txdata = NULL;
          USBx_DEVICE->DIEPEMPMSK &= ~1;
          USBx_OUTEP(0)->DOEPCTL |= USB_OTG_DOEPCTL_CNAK;
        }
      }
    }

    USBx_INEP(0)->DIEPINT = USBx_INEP(0)->DIEPINT;
    USBx_INEP(1)->DIEPINT = USBx_INEP(1)->DIEPINT;
  }

  USBx_DEVICE->DAINT = daint;
  USBx->GOTGINT = gotgint;
  USBx->GINTSTS = gintsts;

}

void usb_outep3_resume_if_paused(void) {
  ENTER_CRITICAL();
  if (!outep3_processing && (USBx_OUTEP(3)->DOEPCTL & USB_OTG_DOEPCTL_NAKSTS) != 0) {
    USBx_OUTEP(3)->DOEPTSIZ = (32U << 19) | 0x800U;
    USBx_OUTEP(3)->DOEPCTL |= USB_OTG_DOEPCTL_EPENA | USB_OTG_DOEPCTL_CNAK;
  }
  EXIT_CRITICAL();
}

void usb_soft_disconnect(bool enable) {
  if (enable) {
    USBx_DEVICE->DCTL |= USB_OTG_DCTL_SDIS;
  } else {
    USBx_DEVICE->DCTL &= ~USB_OTG_DCTL_SDIS;
  }
}
