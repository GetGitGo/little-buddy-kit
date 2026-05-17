#include "ble_bridge.h"
#include <BLE2902.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <Arduino.h>
#include <esp_gap_ble_api.h>

#define NUS_SERVICE_UUID "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define NUS_RX_UUID "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
#define NUS_TX_UUID "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

// talk2littlebuddy/little_ble.py 用此识别固件（不受 macOS 蓝牙名称缓存影响）
static const uint16_t LB_MFG_COMPANY_ID = 0xFFFF;
static const char LB_MFG_PAYLOAD[] = "LB01";

static const size_t RX_CAP = 1024;
static uint8_t rxBuf[RX_CAP];
static volatile size_t rxHead = 0;
static volatile size_t rxTail = 0;

static BLEServer *server = nullptr;
static volatile bool connected = false;

static void rxPush(const uint8_t *p, size_t n) {
  for (size_t i = 0; i < n; i++) {
    size_t next = (rxHead + 1) % RX_CAP;
    if (next == rxTail)
      return;
    rxBuf[rxHead] = p[i];
    rxHead = next;
  }
}

class RxCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    std::string v = c->getValue();
    if (!v.empty())
      rxPush((const uint8_t *)v.data(), v.size());
  }
};

/** 清除 NVS 里 buddy 时代留下的绑定，避免 Mac 与无加密 NUS 冲突 (CBError 14) */
static void bleClearBonds() {
  int n = esp_ble_get_bond_device_num();
  if (n <= 0)
    return;
  esp_ble_bond_dev_t *list =
      (esp_ble_bond_dev_t *)malloc(sizeof(esp_ble_bond_dev_t) * n);
  if (!list)
    return;
  esp_ble_get_bond_device_list(&n, list);
  for (int i = 0; i < n; i++)
    esp_ble_remove_bond_device(list[i].bd_addr);
  free(list);
  Serial.printf("[ble] cleared %d bond(s)\n", n);
}

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *s) override {
    (void)s;
    connected = true;
    Serial.println("[ble] connected");
  }
  void onDisconnect(BLEServer *s) override {
    (void)s;
    connected = false;
    Serial.println("[ble] disconnected");
    BLEDevice::startAdvertising();
  }
};

void bleInit(const char *deviceName) {
  BLEDevice::init(deviceName);
  bleClearBonds();
  BLEDevice::setMTU(517);

  server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());

  BLEService *svc = server->createService(NUS_SERVICE_UUID);

  BLECharacteristic *tx = svc->createCharacteristic(
      NUS_TX_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  tx->addDescriptor(new BLE2902());

  BLECharacteristic *rx = svc->createCharacteristic(
      NUS_RX_UUID,
      BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  rx->setCallbacks(new RxCallbacks());

  svc->start();

  // 勿用 setAdvertisementData 覆盖整包，否则 addServiceUUID 不会出现在空中广播里（Mac 扫不到 NUS）
  std::string mfg;
  mfg.push_back((char)(LB_MFG_COMPANY_ID & 0xFF));
  mfg.push_back((char)((LB_MFG_COMPANY_ID >> 8) & 0xFF));
  mfg.append(LB_MFG_PAYLOAD, sizeof(LB_MFG_PAYLOAD) - 1);
  BLEAdvertisementData scanRsp;
  scanRsp.setName(deviceName);
  scanRsp.setManufacturerData(mfg);

  BLEAdvertising *adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(NUS_SERVICE_UUID);
  adv->setScanResponseData(scanRsp);
  adv->setScanResponse(true);
  adv->setMinPreferred(0x06);
  adv->setMaxPreferred(0x12);
  BLEDevice::startAdvertising();
  Serial.printf("[ble] advertising as '%s' (mfg LB01)\n", deviceName);
}

bool bleConnected() { return connected; }

size_t bleAvailable() { return (rxHead + RX_CAP - rxTail) % RX_CAP; }

int bleRead() {
  if (rxHead == rxTail)
    return -1;
  int b = rxBuf[rxTail];
  rxTail = (rxTail + 1) % RX_CAP;
  return b;
}
