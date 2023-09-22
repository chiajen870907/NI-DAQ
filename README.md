# NI DAQ

----
## 設備
```
擷取卡 :　NI-9234/NI-9215
```
如果沒有設備也可以使用NI MAX 模擬，詳閱[NI MAX](https://knowledge.ni.com/KnowledgeArticleDetails?id=kA03q000000YGdqCAG&l=zh-TW)

Step1. 創建模擬

<img src=".\IMG\Simulation1.png" style="width:50%">

<img src=".\IMG\Simulation2.png" style="width:50%">

Step2. 選擇型號

<img src=".\IMG\Simulation3.png" style="width:20%">

----

## 打包教學
請先打包成EXE
1. ``pip installer -r requirements.txt``
2. ``pyinstaller -F main.py --copy-metadata nidaqmx``
3. 打開main.exe

## 設定教學
<img src=".\IMG\SetUp.png" style="width:50%">

```
physicalChannel :  設定擷取卡的設備名稱，可從NI MAX獲得
Max Val : 根據擷取卡設定最大值
Min Val : 根據擷取卡設定最小值
```
詳情參閱，[擷取卡規格](https://www.ni.com/zh-tw/shop/hardware/products/c-series-voltage-input-module.html)

<img src=".\IMG\SetUp.png" style="width:50%">
根據自己的需求設定轉換倍率與擷取頻率，按下Start即可開始抓取資料
按下Stop後會在自動產生datas資料夾，結果存在datas下檔名格式%Y%m%dT%H%M%S%f

## 備註
本軟體是自己需要抓取切削力而編寫，切削力占用3個Channel，因此有三個Plot視窗，若需要修改請自行修改ui/mainWindow.ui並轉換成py檔。




