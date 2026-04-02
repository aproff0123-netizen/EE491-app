#include <ArduinoBLE.h>

BLEService controlService("19B10000-E8F2-537E-4F6C-D104768A1214");
BLEByteCharacteristic controlChar("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLEWrite);

const int LEFT_LED_PIN = 2;
const int RIGHT_LED_PIN = 4;

void setup() {
  Serial.begin(9600);
  while (!Serial);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(LEFT_LED_PIN, OUTPUT);
  pinMode(RIGHT_LED_PIN, OUTPUT);

  if (!BLE.begin()) {
    Serial.println("BLE failed");
    while (1);
  }

  BLE.setLocalName("UNO R4");
  BLE.setAdvertisedService(controlService);
  controlService.addCharacteristic(controlChar);
  BLE.addService(controlService);
  controlChar.writeValue(0);
  BLE.advertise();
  Serial.println("BLE active");
}

void loop() {
  BLEDevice central = BLE.central();
  if (central) {
    Serial.print("Connected to: ");
    Serial.println(central.address());
    digitalWrite(LED_BUILTIN, HIGH);
    while (central.connected()) {
      BLE.poll();
      
      if (controlChar.written()) {
        uint8_t cmd;
        controlChar.readValue(&cmd, 1);
        Serial.print("Cmd: ");
        Serial.println(cmd);

        if (cmd == 1) {
          digitalWrite(LEFT_LED_PIN, HIGH);
          digitalWrite(RIGHT_LED_PIN, LOW);
          Serial.println("LEFT ON");
        } else if (cmd == 2) {
          digitalWrite(LEFT_LED_PIN, LOW);
          digitalWrite(RIGHT_LED_PIN, HIGH);
          Serial.println("RIGHT ON");
        } else if (cmd == 3) {
          digitalWrite(LEFT_LED_PIN, HIGH);
          digitalWrite(RIGHT_LED_PIN, HIGH);
          Serial.println("BOTH ON");
        } else {
          digitalWrite(LEFT_LED_PIN, LOW);
          digitalWrite(RIGHT_LED_PIN, LOW);
          Serial.println("BOTH OFF");
        }
      }
    }
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("Disconnected");
  }
  BLE.poll();
}
