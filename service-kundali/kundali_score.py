import datetime
import swisseph as swe

class Kundali:
    nadi_map = [
        1,2,3,1,2,3,1,2,3,
        1,2,3,1,2,3,1,2,3,
        1,2,3,1,2,3,1,2,3
    ]

    varna_map = {1: 'Kshatriya', 2: 'Vaishya', 3: 'Shudra', 4: 'Brahmin'}
    varna_chart = {1:1, 2:2, 3:3, 4:4, 5:1, 6:2, 7:3, 8:4, 9:1, 10:2, 11:3, 12:4}

    vashya_groups = {
        1: [1, 2],  # Aries
        2: [2, 7],
        3: [3, 6],
        4: [4, 5],
        5: [5, 4],
        6: [6, 3],
        7: [7, 2],
        8: [8, 12],
        9: [9, 10],
        10: [10, 9],
        11: [11, 12],
        12: [12, 8],
    }

    yoni_map = [
        1,2,3,4,5,6,7,8,9,10,
        11,12,13,14,1,2,3,4,
        5,6,7,8,9,10,11,12,13
    ]

    gana_map = [
        1,2,3,1,2,3,1,2,3,
        1,2,3,1,2,3,1,2,3,
        1,2,3,1,2,3,1,2,3
    ]
    planet_friends = {
        1: [5,9],   # Sun
        2: [1,3,4], # Moon
        3: [1,2],   # Mars
        4: [1,2],   # Mercury
        5: [1,3,4], # Jupiter
        6: [3,4,5], # Venus
        7: [2,5,6], # Saturn
    }

    rashi_lords = {
        1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 4,
        7: 3, 8: 6, 9: 5, 10: 7, 11: 7, 12: 6
    }

    def __init__(self, dob1, dob2, tob1, tob2, lat1, lat2, long1, long2):
        self.dob1 = dob1
        self.dob2 = dob2
        self.time1 = tob1
        self.time2 = tob2 
        self.lat1 = lat1
        self.lat2 = lat2
        self.long1 = long1
        self.long2 = long2

    def get_julian_day(self, date_str, time_str):
        dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
        return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60 + dt.second / 3600)

    def get_moon_position(self, jd, lat, lon):
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        
        # Set geographic location (topocentric calculation)
        swe.set_topo(lon, lat, 0)  # lon, lat, altitude
        moon_pos = swe.calc_ut(jd, swe.MOON, flags)[0]
        return moon_pos[0]

    def get_rashi_nakshatra(self, moon_long):
        nak = int(moon_long / (13 + 1/3)) + 1  # 1 to 27
        rashi = int(moon_long / 30) + 1       # 1 to 12
        return rashi, nak

    # === 1. Varna Matching (1 point) ===

    def match_varna(self, r1, r2):
        return 1 if self.varna_chart[r2] >= self.varna_chart[r1] else 0

    # === 2. Vashya Matching (2 points) ===

    def match_vashya(self, r1, r2):
        return 2 if r2 in self.vashya_groups.get(r1, []) else 0

    # === 3. Tara Matching (3 points) ===
    def match_tara(self, n1, n2):
        tara_diff = abs(n1 - n2)
        bad_taraks = [3, 5, 7, 9, 13]
        return 3 if tara_diff % 9 not in bad_taraks else 0

    # === 4. Yoni Matching (4 points) ===
    # Simplified mapping (1-27 nakshatra mapped to animal 1-14)
    
    def match_yoni(self, n1, n2):
        return 4 if self.yoni_map[n1-1] == self.yoni_map[n2-1] else 0

    # === 5. Graha Maitri Matching (5 points) ===

    def match_grah_maitri(self, r1, r2):
        lord1 = self.rashi_lords[r1]
        lord2 = self.rashi_lords[r2]
        return 5 if lord2 in self.planet_friends.get(lord1, []) else 0

    # === 6. Gana Matching (6 points) ===
    def match_gana(self, n1, n2):
        return 6 if self.gana_map[n1-1] == self.gana_map[n2-1] else 0

    # === 7. Bhakoot Matching (7 points) ===
    def match_bhakoot(self, r1, r2):
        # Ideal if Rashi difference ≠ 6, 8
        diff = abs(r1 - r2)
        return 7 if diff not in [6, 8] else 0

    # === 8. Nadi Matching (8 points) ===
    
    def match_nadi(self, n1, n2):
        return 0 if self.nadi_map[n1-1] == self.nadi_map[n2-1] else 8

    # === Main Function ===
    def get_guna_score(self):
        jd1 = self.get_julian_day(self.dob1, self.time1)
        jd2 = self.get_julian_day(self.dob2, self.time2)

        moon1 = self.get_moon_position(jd1, self.lat1, self.long1)
        moon2 = self.get_moon_position(jd2, self.lat2, self.long2)

        r1, n1 = self.get_rashi_nakshatra(moon1)
        r2, n2 = self.get_rashi_nakshatra(moon2)

        #print(f"Person 1: Rashi {r1}, Nakshatra {n1}")
        #print(f"Person 2: Rashi {r2}, Nakshatra {n2}")

        total = 0
        total += self.match_varna(r1, r2)
        total += self.match_vashya(r1, r2)
        total += self.match_tara(n1, n2)
        total += self.match_yoni(n1, n2)
        total += self.match_grah_maitri(r1, r2)
        total += self.match_gana(n1, n2)
        total += self.match_bhakoot(r1, r2)
        total += self.match_nadi(n1, n2)

        return total
