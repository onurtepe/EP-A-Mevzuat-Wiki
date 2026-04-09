import ingest

url = 'http://www.mevzuat.gov.tr/Metin1.Aspx?MevzuatKod=1.5.6446&MevzuatIliski=0&sourceXmlSearch=6446&Tur=1&Tertip=5&No=6446'

params = ingest.parse_mevzuat_no(url)
print('Params:', params)

text = ingest.fetch_mevzuat_xml(*params)
print('Metin uzunlugu:', len(text))
print('Ilk 300 karakter:')
print(text[:300])
