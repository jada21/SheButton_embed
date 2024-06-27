#include <Arduino.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>   
#include <string>
#include <cstdlib>

String receivedData;
String incomingData;
String latVal, lngVal, tempVal2;
bool successFlag;

const char* WIFI_USER = <yourWifiUserHere>;        
const char* WIFI_PASS = <yourWifiPasswordHere>;

void setup() 
{
  successFlag = false;
  //Set up Lora 
  Serial.begin(115200);
  Serial2.begin(115200);
  delay(5000);
  Serial2.println("AT\r\n");
  Serial2.println("AT+ADDRESS=22\r\n");
  Serial2.println("AT+NETWORKID=3\r\n");
  updateSerial();
  Serial.println("start");
  Serial2.println("AT\r\n");
  updateSerial();
  delay(100);
  Serial2.println("+RCV=21,30\r\n");
  updateSerial();
  Serial.println("code 1");
  delay(100);
  
  //Set up WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_USER, WIFI_PASS);
  Serial.println("Connecting");

  while(WiFi.status() != WL_CONNECTED)    
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" ");
  Serial.print("Connected to WiFi network with IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() 
{
  updateSerial();
  delay(40);
  incomingData = Serial2.readString();
  updateSerial();
  Serial.println("incomin data: " + incomingData);
  receivedData = "";
  for(int i=11; i<= incomingData.length();i++)
  {
    receivedData += incomingData[i];
  }
  Serial.println("received data: " + receivedData);
  parseData(receivedData);
  delay(10);

  if (WiFi.status() == WL_CONNECTED)
  {
    String endpoint = <yourAPILinkHere>;
    HTTPClient http;  
    http.begin(endpoint);
    Serial.println("connected to endpoint");
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<1024> doc;               // Empty JSONDocument
    String httpRequestData;                     //Emtpy string to be used to store HTTP request data string
    String http_response;

    if (successFlag == true)
    {
      //POST REQUEST:
      Serial.println("POST REQUEST");
      doc["lat"] = latVal;
      doc["lng"] = lngVal;
      doc["temp"] = tempVal2;

      serializeJson(doc, httpRequestData);    //copies json doc into httpRequestData
      int httpResponseCode = http.POST(httpRequestData);   //POST REQUEST, returns response code
      if (httpResponseCode>0) 
      {
        Serial.print("HTTP Response code from request: ");
        Serial.println(httpResponseCode);
        Serial.print("HTTP Response from server: ");
        http_response = http.getString();
        Serial.println(http_response);
        Serial.println(" ");
        Serial.println("Posted:" + latVal + " " + lngVal + " " + tempVal2 + " ");
      }
      else                                      //if http response code is negative
      {
        Serial.print("Error code: ");
        http_response = http.getString();
        Serial.println(httpResponseCode);
      }
      http.end();
      delay(1000);
    

      //GET REQUEST:
      Serial.println("GET REQUEST");
      http.begin(endpoint);

      int httpResponseCode2 = http.GET();      //performs get request and receives status code response
      
      if (httpResponseCode2>0) 
      {
        Serial.print("HTTP Response code: ");
        Serial.println(httpResponseCode2);

        Serial.print("Response from server: ");
        http_response = http.getString();       //gets worded/verbose response
        Serial.println(http_response);
      }
      else 
      {
        Serial.print("Error code: ");
        Serial.println(httpResponseCode2);
        Serial.print("error message: ");
        http_response = http.getString();       //gets worded/verbose response
        Serial.println(http_response);
      }
      
      StaticJsonDocument<1024> doc1;            //document to store deserialized json
      DeserializationError error = deserializeJson(doc1, http_response);
      if (error) 
      {
        Serial.print("Could not deserialize json");
        Serial.println(error.c_str());
      }
      const bool status_flag = doc1["status"];
      Serial.println("Status flag: " + status_flag);     
      http.end();

      if (status_flag ==1)
      {
        Serial.println("omg can u send");
        Serial2.println("AT+SEND=21,5,1\r\n");
        updateSerial();
        delay(500);
      }
    }
    successFlag = false;
  }
  else 
  {
    Serial.println("WiFi Disconnected");
  }
  delay(500);
}


void parseData(String data) 
{
  int comma1Index = data.indexOf(',');
  if (comma1Index != -1) 
  {
    Serial.println("code 3");
    int comma2Index = data.indexOf(',', comma1Index + 1);
    int comma3Index = data.indexOf(',', comma2Index + 1);

    Serial.println("code 4");
    latVal = data.substring(0, comma1Index);
    lngVal = data.substring(comma1Index + 1, comma2Index);
    String tempVal = data.substring(comma2Index + 1, comma3Index);
    tempVal2 = tempVal.substring(0, 2);  //for some reason additional values are at end of temp therefore make new temp val with only 2 characters of original temp

    Serial.println("code is here");
    Serial.println("lat value: " + latVal);
    Serial.println("long value: " + lngVal);
    Serial.println("temp value: " + tempVal2);
    successFlag = true;
    delay(50);
  }
}

void updateSerial() 
{
  delay(200);
  while (Serial.available()) 
  {
    Serial2.write(Serial.read());
  }
  while (Serial2.available()) 
  {
    Serial.write(Serial2.read());
  }
}

