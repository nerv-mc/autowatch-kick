import sqlite3
import re

# File database tujuan
DB_NAME = "drops.db"

# Data mentah rekap histori milikmu
RAW_REKAP_TEXT = """
TJR
dcampion
kendace
duelbj
alyyy_xxx
blakjac21
redwings944
imbones2
Sangtar
coconut
JtzCast
funnyhoodvidz
blonderabbit
keithlocks
Jamie
AverageAden
bigfoltz
frankdimes
BIGBOSSFF
Drago
auslots
cocospinzz
CUSTOMK
NeshyKing
ludopatos
DeMize
GrayGray
Tyceno
LosPollosTV
CUSTOMK
Ryan6021
Sav21
demise
vasheeesh
classicnative
imbones
funnyhoodvidz
ClassyBeef
anthospins
wassimostv
ReachAces
keithlocks
Lance
Bernie
runalong
Kukudota2
scrapes
cocospinzz
berserk-cs2
Doge
ADukes
DeMize
Gkbaby
Sangtar
Bigfoltz
Casiibro
kranzzofficial
starladder
starladder
mascoobs
AllonBlack1919
theslotkiller
BlondeRabbit
slaeh
LosPollosTV
Tyceno
starladder
kingeen
starladder
JackpotMarki
Doge
GrayGray
starladder
starladder
starladder
Eddie
Eddie
Sav21
DeMiZe
imbones
YungKarth
fastnslow
Lucky_girl13
Schneckyirl
Locov2
Syztmz
agony
CUSTOMK
sehamx
jaekcreates
dynamikyt
juke
cocospinzz
dcampion
novaneon
festlm
Hanvee
Doge
bath_dalts
Apploeninja
keithlocks
keithlocks
Classybeef
Bigfoltz
blakjac21
wino87
devorek
Tyceno
zombs
omie
BTCs
ChuckyBTZ
Eddie
Eddie
Eddie
gamblingjohn
ChuckyBTZ
Warren
LowLimit
Lance
newname
BTCs
Abstract2
TCKGG
xwonn
Sneakzy
Bandz
nosedivegambles
mascoobs
Foss
CUSTOMK
BenDaDonnn
keithlocks
LosPollosTV
dcampion
realgafi
LeonNoLimit
TheRealPatty
Dosekai
abstract2
imbones
keithlocks
DeMize
TJR
TheGoobr
schneckyirl
icesol
mintpod2
jonjiponji
Zlatar
kingdodotv
water
reachaces
kyootbot
schlump
real_hyphonix
OVOPhantuums
Fornixtuned
daybeats
natankraken
Tyceno
Classybeef
GrayGray
haddzyjr
ramee
JackpotMarki
jackdoherty
sonecarox
katanatw
betwithkevin
shoovy
szymool
moonlight2019
magicaldota
cocospinzz
dcampion
ADukes
SiscoKid
dokkorki
dynamikyt
agony
ryda
ZombieBarricades
dcampion
SiscoKid
dokkorki
dynamikyt
ZombieBarricades
prophetgg
dustin
DDG
CUSTOMK
vasheeesh
wymzi
Softypawz
bandz
oblivionsw
Doge
keithlocks
ChuckyBTZ
"""

def seed_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Pastikan tabel streamer_drops sudah dibuat
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS streamer_drops (
            username TEXT PRIMARY KEY,
            drop_count INTEGER DEFAULT 1,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Bersihkan & parsing teks rekap (jadikan lowercase agar tidak terduplikasi)
    lines = [line.strip().lower() for line in RAW_REKAP_TEXT.strip().split('\n') if line.strip()]
    
    # Hitung frekuensi tiap streamer
    frequency_map = {}
    for streamer in lines:
        frequency_map[streamer] = frequency_map.get(streamer, 0) + 1

    # Masukkan/Perbarui data di database
    inserted_count = 0
    updated_count = 0

    for streamer, count in frequency_map.items():
        cursor.execute('''
            INSERT INTO streamer_drops (username, drop_count)
            VALUES (?, ?)
            ON CONFLICT(username) DO UPDATE SET
                drop_count = MAX(streamer_drops.drop_count, excluded.drop_count),
                last_updated = CURRENT_TIMESTAMP
        ''', (streamer, count))
        
        if cursor.rowcount > 0:
            inserted_count += 1

    conn.commit()
    conn.close()

    print(f"✓ Berhasil memproses {len(lines)} entri rekap!")
    print(f"✓ Total {len(frequency_map)} streamer unik telah diinput/diperbarui di {DB_NAME}.")

if __name__ == "__main__":
    seed_database()