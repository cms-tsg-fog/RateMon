Instructions from Sam:

python compareWBMTriggerRates.py 251883 --steamRates steam25ns.csv --targetLumi 7000 --minLS 200 --maxLS 400
obviously, with the runnr and lumi sections changed.

note here is the rub, you need to first have kerberous ticket  and set the envir variable to SSO_COOKIE to the location of a soon to be created cookie file. I have it set to /afs/cern.ch/user/s/sharper/secure/ssocookie.txt (note it shoudl be in a private directory, anybody with this cookie can sign on as you)
and do:
cern-get-sso-cookie --krb -r -u https://cmswbm.web.cern.ch/cmswbm -o $SSO_COOKIE

My code will alert you if you dont have it defined or a cookie. The one thing is that it can sometimes expire in a werid way so if the script crashes, do another
cern-get-sso-cookie --krb -r -u https://cmswbm.web.cern.ch/cmswbm -o $SSO_COOKIE

This outputs a format sutable for  a comma seperated value file which  you can then upload to google docs which gives you something like this
https://docs.google.com/spreadsheets/d/1hdJWZx6L8vWc-Du__Og4x6KSPbLlEtZsNZpt2SNfEss/edit?usp=sharing
It only outputs unprescaled (at HLT) triggers.
