Output docs/evidence/render-live-demo.gif

Set Shell "bash"
Set FontSize 14
Set Width 1400
Set Height 620
Set Padding 20
Set TypingSpeed 25ms
Set Framerate 24

Hide
Type "export PS1='$ '"
Enter
Type "clear"
Enter
Sleep 300ms
Show

Type `curl -sS -w '\nHTTP:%{http_code}\n' -X POST https://sonora-crop-yield-estimator-cd8z.onrender.com/predict -H 'Content-Type: application/json' -d '{"Nommunicipio":"Hermosillo","Nomcicloproductivo":"Otoño-Invierno","Nommodalidad":"Riego","Nomcultivo":"Trigo grano","Sembrada":1200.0}'`
Enter

Sleep 5s
