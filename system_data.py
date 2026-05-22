import numpy as np
from scipy.spatial.transform import Rotation as R
from dataclasses import dataclass
from enum import Enum, auto

pairs0 = (
    "ABOUSEITILETSTONLONUTHNOALLEXEGEZACEBISOUSESARMAINDIREA.ERATENBERALAVETIEDORQUANTEISRION"
)
fist = 0 #contains info about criminal actvity in system, needs passing in future
token_strings = {
    128: "AL",
    129: "LE",
    130: "XE",
    131: "GE",
    132: "ZA",
    133: "CE",
    134: "BI",
    135: "SO",
    136: "US",
    137: "ES",
    138: "AR",
    139: "MA",
    140: "IN",
    141: "DI",
    142: "RE",
    143: "A",
    144: "ER",
    145: "AT",
    146: "EN",
    147: "BE",
    148: "RA",
    149: "LA",
    150: "VE",
    151: "TI",
    152: "ED",
    153: "OR",
    154: "QU",
    155: "AN",
    156: "TE",
    157: "IS",
    158: "RI",
    159: "ON",
}

desc_list = [
    # 0x81 (129)
    ["fabled", "notable", "well known", "famous", "noted"],
    ["very", "mildly", "most", "reasonably", ""],
    ["ancient", "\x95", "great", "vast", "pink"],
    ["\x9E \x9D plantations", "mountains", "\x9C", "\x94 forests", "oceans"],
    ["shyness", "silliness", "mating traditions", "loathing of \x86", "love for \x86"],
    ["food blenders", "tourists", "poetry", "discos", "\x8E"],
    ["talking tree", "crab", "bat", "lobst", "\xB2"],
    ["beset", "plagued", "ravaged", "cursed", "scourged"],
    ["\x96 civil war", "\x9B \x98 \x99s", "a \x9B disease", "\x96 earthquakes", "\x96 solar activity"],
    ["its \x83 \x84", "the \xB1 \x98 \x99", "its inhabitants' \x9A \x85", "\xA1", "its \x8D \x8E"],
    ["juice", "brandy", "water", "brew", "gargle blasters"],
    ["\xB2", "\xB1 \x99", "\xB1 \xB2", "\xB1 \x9B", "\x9B \xB2"],
    ["fabulous", "exotic", "hoopy", "unusual", "exciting"],
    ["cuisine", "night life", "casinos", "sit coms", " \xA1 "],
    ["\xB0", "The planet \xB0", "The world \xB0", "This planet", "This world"],
    ["n unremarkable", " boring", " dull", " tedious", " revolting"],
    ["planet", "world", "place", "little planet", "dump"],
    ["wasp", "moth", "grub", "ant", "\xB2"],
    ["poet", "arts graduate", "yak", "snail", "slug"],
    ["tropical", "dense", "rain", "impenetrable", "exuberant"],
    ["funny", "wierd", "unusual", "strange", "peculiar"],
    ["frequent", "occasional", "unpredictable", "dreadful", "deadly"],
    ["\x82 \x81 for \x8A", "\x82 \x81 for \x8A and \x8A", "\x88 by \x89", "\x82 \x81 for \x8A but \x88 by \x89", "a\x90 \x91"],
    ["\x9B", "mountain", "edible", "tree", "spotted"],
    ["\x9F", "\xA0", "\x87oid", "\x93", "\x92"],
    ["ancient", "exceptional", "eccentric", "ingrained", "\x95"],
    ["killer", "deadly", "evil", "lethal", "vicious"],
    ["parking meters", "dust clouds", "ice bergs", "rock formations", "volcanoes"],
    ["plant", "tulip", "banana", "corn", "\xB2weed"],
    ["\xB2", "\xB1 \xB2", "\xB1 \x9B", "inhabitant", "\xB1 \xB2"],
    ["shrew", "beast", "bison", "snake", "wolf"],
    ["leopard", "cat", "monkey", "goat", "fish"],
    ["\x8C \x8B", "\xB1 \x9F \xA2", "its \x8D \xA0 \xA2", "\xA3 \xA4", "\x8C \x8B"],
    ["meat", "cutlet", "steak", "burgers", "soup"],
    ["ice", "mud", "Zero-G", "vacuum", "\xB1 ultra"],
    ["hockey", "cricket", "karate", "polo", "tennis"],
]

class ObjectType(Enum):
    STAR = auto()
    PLANET = auto()

@dataclass
class SystemData:
    number:int
    name: str
    prosperity: int
    prosperity_str: str
    economy: int
    economy_str: str
    economyType: int
    economyType_str: str
    economy_trade_value: int
    government: int
    government_str: str
    tech_level: int
    population: float
    speciesType: str
    grossProductivity: int
    averageRadius: int
    x: int
    y: int
    longRangeSize: int
    shortRangeSize:int
    sunCoords: tuple = (0,0,0)
    planetCoords: tuple = (0,0,0)
    description: str = ""

@dataclass
class CelestialObject:
    """Represents a celestial object with position and properties."""
    position: np.ndarray
    radius: float
    name: str
    obj_type: ObjectType
    color: tuple = (255, 255, 255)

class Planet_and_Star:
    """Manages astronomical data for the solar system."""
    def __init__(self, planet_position, star_position,system_name):
        
        self.objects = {
            'planet': CelestialObject(
                position=planet_position,
                radius=24576,
                name="planet",
                obj_type=ObjectType.PLANET,
                color=set_planet_color(system_name)
            ),
            'sun': CelestialObject(
                position=star_position,
                radius=24576,
                name="Sun",
                obj_type=ObjectType.STAR,
                color=(255, 255, 150)
            )
        }

def set_planet_color(system_name):
    """Set planet color based on system name hash."""
    hash_value = sum(ord(c) for c in system_name)
    r = (hash_value * 109) % 256
    g = (hash_value * 73) % 256
    b = (hash_value * 37) % 256
    return (r, g, b)

def get_spaceStation_coords(planet_center, planet_radius=24576, offset=40960):
    """
    Place the station between the player (0,0,0) and the planet center,
    just above the planet's surface (planet_radius + offset).
    """
    player_pos = np.array([0.0, 0.0, 0.0])
    planet_center = np.array(planet_center, dtype=float)
    direction = planet_center - player_pos
    norm = np.linalg.norm(direction)
    if norm == 0:
        # Fallback: place at default offset along z
        return np.array([0, 0, planet_radius + offset])
    direction = direction / norm

    # Find two perpendicular vectors to 'direction' to define a plane
    # Use Gram-Schmidt: pick any vector not parallel to direction
    if abs(direction[0]) < 0.9:
        v = np.array([1, 0, 0])
    else:
        v = np.array([0, 1, 0])
    perp1 = np.cross(direction, v)
    perp1 /= np.linalg.norm(perp1)
    perp2 = np.cross(direction, perp1)
    perp2 /= np.linalg.norm(perp2)

    # Random offset in the perpendicular plane (up to 10% of planet_radius)
    r = np.random.uniform(0, 0.1 * planet_radius)
    angle = np.random.uniform(0, 2 * np.pi)
    offset_vec = np.cos(angle) * perp1 + np.sin(angle) * perp2
    offset_vec *= r

    # Place station just above the planet surface, with random perpendicular offset
    station_pos = planet_center - direction * (planet_radius + offset) + offset_vec
    return station_pos

def get_station_orientation_towards_planet(station_pos, planet_pos, port_normal=np.array([0, 0, 1])):
        direction = np.array(planet_pos) - np.array(station_pos)
        direction = direction / np.linalg.norm(direction)
        # Find rotation from port_normal to direction
        result = R.align_vectors([direction], [port_normal])
        rot = result[0]
        return rot.as_euler('xyz')  # or rot.as_quat() for quaternion


def twist_seeds(QQ15):
    s0 = int.from_bytes(QQ15[0:2], 'little')
    s1 = int.from_bytes(QQ15[2:4], 'little')
    s2 = int.from_bytes(QQ15[4:6], 'little')

    tmp = s0 + s1
    s0 = s1 & 0xFFFF
    s1 = s2 & 0xFFFF
    s2_sum = (tmp & 0xFFFF) + s1
    s2 = s2_sum & 0xFFFF

    QQ15[0:2] = s0.to_bytes(2, 'little')
    QQ15[2:4] = s1.to_bytes(2, 'little')
    QQ15[4:6] = s2.to_bytes(2, 'little')
    
    
    
    return QQ15

def set_galaxy(galaxy_number, seeds):
    for _ in range(galaxy_number):
        for i in range(len(seeds)):
            seeds[i] = ((seeds[i] << 1) & 0xFF) | ((seeds[i] >> 7) & 0x01)

    return seeds  

def getSystemName(seeds):
    local_seeds = seeds.copy()
    bit6 = (local_seeds[0] >> 6) & 1
    loops = 3 if bit6 == 0 else 4
    

    name_parts = []
    for _ in range(loops):
        value = local_seeds[5] & 0b00011111
        if value != 0:
            token = token_strings[value + 128]
            name_parts.append(token)
        local_seeds= twist_seeds(local_seeds)
    
    s0_high = local_seeds[1]
    s1_high = local_seeds[3]
    if s0_high + s1_high > 255:
        carry=1
    else:
        carry=0

    return "".join(name_parts),carry

def getEconomy(seeds):
    local_seeds = seeds.copy()
    s0_high = local_seeds[1]
    bit_2 = (s0_high & 0b100) >> 2
    
    if bit_2 == 0:
        str = "Industrial"
    else:
        str = "Agricultural"
    
    return bit_2,str

def getProsperity(seeds,government):
    
    local_seeds = seeds.copy()
    s0_high = local_seeds[1]
    bit0_2 = (s0_high & 0b111)

    if government == 0 or government==1:  # Anarchy or Feudal
        bit0_2 = (bit0_2  | 0b10)

    if bit0_2 == 0 or bit0_2 == 5:
        str = "Rich"
    elif bit0_2 == 1 or bit0_2 == 6:
        str = "Average"
    elif bit0_2 == 2 or bit0_2 == 7:
        str = "Poor"   
    elif bit0_2 == 3 or bit0_2 == 4:
        str = "Mainly"
    else:
        str = "Unknown"    
    return bit0_2,str

def getEconomyType(prosperity_str, economy_str):
    if prosperity_str == "Rich" and economy_str == "Industrial":
        return 0, prosperity_str+" "+economy_str,0
    elif prosperity_str == "Average" and economy_str == "Industrial":
        return 1, prosperity_str+" "+economy_str,1
    elif prosperity_str == "Poor" and economy_str == "Industrial":
        return 2, prosperity_str+" "+economy_str,2
    elif prosperity_str == "Mainly" and economy_str == "Industrial":
        return 3, prosperity_str+" "+economy_str,3
    elif prosperity_str == "Mainly" and economy_str == "Agricultural":
        return 7, prosperity_str+" "+economy_str ,4 
    elif prosperity_str == "Rich" and economy_str == "Agricultural":
        return 4, prosperity_str+" "+economy_str,5
    elif prosperity_str == "Average" and economy_str == "Agricultural":
        return 5, prosperity_str+" "+economy_str,6
    elif prosperity_str == "Poor" and economy_str == "Agricultural":
        return 6, prosperity_str+" "+economy_str,7
      
    else:  
        return -1, "Unknown",-1    

def getGovernment(seeds):
    local_seeds = seeds.copy()
    s1_lo = local_seeds[2]
    gov_bits = (s1_lo & 0b00111000) >> 3
    if gov_bits == 0:
        return gov_bits,"Anarchy"
    elif gov_bits == 1:
        return gov_bits,"Feudal"
    elif gov_bits == 2:
        return gov_bits,"Multi-Government"
    elif gov_bits == 3:
        return gov_bits,"Dictatorship"
    elif gov_bits == 4:
        return gov_bits,"Communist"
    elif gov_bits == 5:
        return gov_bits,"Confederacy"
    elif gov_bits == 6:
        return gov_bits,"Democracy"
    elif gov_bits == 7:
        return gov_bits,"Corporate State"
    else:
        return gov_bits,"Unknown"

def getTechLevel(seeds, prosperity,economy,government):
    local_seeds = seeds.copy()
    s1_high = local_seeds[3]
    s1_high = s1_high & 0b11
    flipped_prosperity = (~prosperity & 0b111)
    government_component = (government+1)//2
    tech_level = flipped_prosperity + s1_high + government_component+1
    return tech_level

def getPoulation(tech_level, prosperity, government):
    pop = ((tech_level-1) * 4) + prosperity + government +1
    return  pop/10

def getSpeciesType(seeds):
    local_seeds = seeds.copy()
    is_alien = (local_seeds[4]& 0b10000000)>>7
    if is_alien==   0:
        return "Human Colonials"
    else:
        speciesType = ""
        description = (local_seeds[5]& 0b00011100)>>2
        if description == 0:
            speciesType += "Large"
        elif description == 1:
            speciesType += "Fierce"
        elif description == 2:
            speciesType += "Small"
        
        description = (local_seeds[5]& 0b11100000)>>5
        if description == 0:
            speciesType += " Green"
        elif description == 1:
            speciesType += " Red"
        elif description == 2:    
            speciesType += " Yellow"
        elif description == 3:    
            speciesType += " Blue"
        elif description == 4:    
            speciesType += " Black"
        elif description == 5:    
            speciesType += " Harmless"

        s0_high = local_seeds[1]
        s1_high = local_seeds[3]
        description = (s0_high ^ s1_high) & 0b00000111
        if description == 0:
            speciesType += " Slimy"
        elif description == 1:
            speciesType += " Bug-Eyed"
        elif description == 2:    
            speciesType += " Horned"
        elif description == 3:    
            speciesType += " Bony"
        elif description == 4:    
            speciesType += " Fat"
        elif description == 5:    
            speciesType += " Furry"

        s2_high = local_seeds[5] & 0b00000011
        description = (description + s2_high) & 0b00000111
        if description == 0:
            speciesType += " Rodents"
        elif description == 1:
            speciesType += " Frogs"
        elif description == 2:  
            speciesType += " Lizards"
        elif description == 3:  
            speciesType += " Lobsters"
        elif description == 4:  
            speciesType += " Birds"
        elif description == 5:  
            speciesType += " Humanoids"
        elif description == 6:  
            speciesType += " Felines"
        elif description == 7:
            speciesType += " Insects"               

        return speciesType.lstrip()

def getGrossProductivity(prosperity,government, population):
    flipped_prosperity = (~prosperity & 0b111)
    productivity =  (flipped_prosperity + 3) * (government+4) * population *8

    return int(productivity*10)

def getAverageRadius(seeds):
    s2_high = seeds[5] & 0b00001111
    s1_high = seeds[3] 
    averageRadius =(s2_high+11) *256 + s1_high
    return int(averageRadius)

def getXY(seeds):
    x = s1_high = seeds[3]
    y= s0_high = seeds[1]>>1
    
    return x, y

def getLongRangeSize(seeds):
    size = s2_lo = seeds[4] | 0b01010000
    if size <80:
        size = 3
    elif size >143:
        size=1
    else:
        size = 2
    return size

def getShortRangeSize(seeds,carry):
    s2_hi = seeds[5] & 0x1
    size = s2_hi +2 + carry
    return size

def getPlanetXYZ(seeds,fist):
    z = s0_high = seeds[1] &0b00000111
    fist_bit0 = (fist & 0b1)
    z= (z+6+fist_bit0)
    carry = z &0b00000001
    z= z>>1

    x = z>>1
    if carry==1:
        x=-x
    
    y=x

    return(x*100,y*100,z*100)

def getSunXYZ(seeds):
    z = s1_high = seeds[3]
    z=(z & 0b00000111) | 0b00000001 
    
    x = s2_high = seeds[5]
    x= x & 0b00000011
    y=x

    return (x*100,y*100,-z*100) 

def gen_rnd_number(rnd_seed):
    #Based on Ian Bell's C language implementation of text Elite.
    x = (rnd_seed['a'] * 2) & 0xFF
    a = x + rnd_seed['c']
    if rnd_seed['a'] > 127:
        a += 1
    rnd_seed['a'] = a & 0xFF
    rnd_seed['c'] = x

    carry = a // 256  # a = any carry left from above
    x = rnd_seed['b']
    a = (carry + x + rnd_seed['d']) & 0xFF
    rnd_seed['b'] = a
    rnd_seed['d'] = x
    return a

def goat_soup(source, psy, rnd_seed):
   #Based on Ian Bell's C language implementation of text Elite.
    
    i = 0
    output = ""
    while i < len(source):
        c = source[i]
        i += 1
        if isinstance(c, str):
            c = ord(c)
        if c < 0x80:
            output += chr(c)
        elif c <= 0xA4:
            rnd = gen_rnd_number(rnd_seed)
            idx = (rnd >= 0x33) + (rnd >= 0x66) + (rnd >= 0x99) + (rnd >= 0xCC)
            option = desc_list[c - 0x81][idx]
            output += goat_soup(option, psy, rnd_seed)
        else:
            if c == 0xB0:  # planet name
                output += psy['name'][0].upper() + psy['name'][1:].lower()
            elif c == 0xB1:  # planet name + "ian"
                name = psy['name']
                if name[-1] in "EI":
                    name = name[:-1]
                output += name.capitalize() + "ian"
            elif c == 0xB2:  # random name
                length = gen_rnd_number(rnd_seed) & 3
                for j in range(length + 1):
                    x = gen_rnd_number(rnd_seed) & 0x3e
                    if j == 0:
                        output += pairs0[x].upper()
                    else:
                        output += pairs0[x].lower()
                    output += pairs0[x+1].lower()
            else:
                output += f"<bad char in data [{c:X}]>"
    return output

def get_all_system_data(galaxy_number=0):

    if galaxy_number < 0 or galaxy_number > 7:
        galaxy_number = 0
        
    all_system_data = []

    original_seeds = [0x4A, 0x5A, 0x48, 0x02, 0x53, 0xB7]  # Example seed values
    seeds=original_seeds.copy()

    seeds = set_galaxy(galaxy_number, seeds)  # Set to galaxy 0 for this example
    template = "\x8F is \x97."

    for i in range (256):

        name,carry = getSystemName(seeds)
        government,government_str = getGovernment(seeds)
        prosperity, prosperity_str = getProsperity(seeds,government)
        economy, economy_str = getEconomy(seeds)
        economyType, economyType_str, trade_value = getEconomyType(prosperity_str, economy_str)
        government,government_str = getGovernment(seeds)
        tech_level= getTechLevel(seeds, prosperity,economy,government)
        population = getPoulation(tech_level, prosperity, government)
        speciesType = getSpeciesType(seeds)
        grossProductivity = getGrossProductivity(prosperity,government, population)
        averageRadius = getAverageRadius(seeds)
        x, y = getXY(seeds)
        longRangeSize = getLongRangeSize(seeds)
        shortRangeSize = getShortRangeSize(seeds,carry)
        unit= 65536 / 100
        sunCoords = getSunXYZ(seeds)
        planetCoords = getPlanetXYZ(seeds,fist)
        sunCoords = (sunCoords[0]*unit,sunCoords[1]*unit,sunCoords[2]*unit)
        planetCoords = (planetCoords[0]*unit,planetCoords[1]*unit,planetCoords[2]*unit)
        desc_seeds = seeds.copy()
        d_seeds = {'a': desc_seeds[2], 'b': desc_seeds[3], 'c': desc_seeds[4], 'd': desc_seeds[5]}
        description = goat_soup(template, {'name': name}, d_seeds)

        #description overrides for specific systems - there are only 3 valid ones in the whole game
        if galaxy_number == 0 and i==211: #TEORGE
            description = "The colonists here have violated INTERGALACTIC CLONING PROTOCOL and should be avoided"
        elif galaxy_number == 2 and i==100: #ARREDI
            description = "COMING SOON: ELITE II"
        elif galaxy_number == 2 and i==41: #ANREER
            description = "the inhabitants of Anreer are so amazingly primitive that they still think ***** ****** is 3D"

        new_system = SystemData(number = i,
                                name=name, 
                                prosperity=prosperity, prosperity_str=prosperity_str,
                                economy=economy, economy_str=economy_str,
                                economyType=economyType, economyType_str=economyType_str,
                                economy_trade_value = trade_value,
                                government=government, government_str=government_str,
                                tech_level=tech_level,
                                population=population,
                                speciesType=speciesType,
                                grossProductivity=grossProductivity,
                                averageRadius=averageRadius, 
                                x=x,
                                y=y,
                                longRangeSize=longRangeSize,
                                shortRangeSize=shortRangeSize,
                                sunCoords=sunCoords,
                                planetCoords=planetCoords,
                                description=description
                                )
        
        
        all_system_data.append(new_system)
        
        for _ in range(4):  # Twist the seeds 4 times
            twist_seeds(seeds)

            
    """
    for system in all_system_data:
        if system.name == "LAVE":
            print(f"Number: {system.number}")
            print(f"Name: {system.name}")
            print(f"Prosperity: {system.prosperity} ({system.prosperity_str})")
            print(f"Economy: {system.economy} ({system.economy_str})")
            print(f"Economy Type: {system.economyType} ({system.economyType_str})")
            print(f"Government: {system.government} ({system.government_str})")
            print(f"Tech Level: {system.tech_level}")
            print(f"Population: {system.population}")
            print(f"Species Type: {system.speciesType}")
            print(f"Gross Productivity: {system.grossProductivity}")
            print(f"Average Radius: {system.averageRadius}")
            print(f"Coordinates: ({system.x}, {system.y})") 
            print(f"Long Range Size: {system.longRangeSize}")
            print(f"Short Range Size: {system.shortRangeSize}")
            print(f"Sun Coordinates: {system.sunCoords}")
            print(f"Planet Coordinates: {system.planetCoords}")
            print(f"Description: {system.description}")
    """
    return all_system_data