
COMMODITIES = {
    "Food": {
        "id": 0,
        "base_price": 19,
        "econ_factor": -2,
        "unit": "t",
        "base_quantity": 6,
        "mask": 0b00000001,  # 1
        "string": "Food",
    },
    "Textiles": {
        "id": 1,
        "base_price": 20,
        "econ_factor": -1,
        "unit": "t",
        "base_quantity": 10,
        "mask": 0b00000011,  # 3
        "string": "Textiles",
    },
    "Radioactives": {
        "id": 2,
        "base_price": 65,
        "econ_factor": -3,
        "unit": "t",
        "base_quantity": 2,
        "mask": 0b00000111,  # 7
        "string": "Radioactives",
    },
    "Slaves": {
        "id": 3,
        "base_price": 40,
        "econ_factor": -5,
        "unit": "t",
        "base_quantity": 226,
        "mask": 0b00011111,  # 31
        "string": "Slaves",
    },
    "Liquor/Wines": {
        "id": 4,
        "base_price": 83,
        "econ_factor": -5,
        "unit": "t",
        "base_quantity": 251,
        "mask": 0b00001111,  # 15
        "string": "Liquor/Wines",
    },
    "Luxuries": {
        "id": 5,
        "base_price": 196,
        "econ_factor": 8,
        "unit": "t",
        "base_quantity": 54,
        "mask": 0b00000011,  # 3
        "string": "Luxuries",
    },
    "Narcotics": {
        "id": 6,
        "base_price": 235,
        "econ_factor": 29,
        "unit": "t",
        "base_quantity": 8,
        "mask": 0b01111000,  # 120
        "string": "Narcotics",
    },
    "Computers": {
        "id": 7,
        "base_price": 154,
        "econ_factor": 14,
        "unit": "t",
        "base_quantity": 56,
        "mask": 0b00000011,  # 3
        "string": "Computers",
    },
    "Machinery": {
        "id": 8,
        "base_price": 117,
        "econ_factor": 6,
        "unit": "t",
        "base_quantity": 40,
        "mask": 0b00000111,  # 7
        "string": "Machinery",
    },
    "Alloys": {
        "id": 9,
        "base_price": 78,
        "econ_factor": 1,
        "unit": "t",
        "base_quantity": 17,
        "mask": 0b00011111,  # 31
        "string": "Alloys",
    },
    "Firearms": {
        "id": 10,
        "base_price": 124,
        "econ_factor": 13,
        "unit": "t",
        "base_quantity": 29,
        "mask": 0b00000111,  # 7
        "string": "Firearms",
    },
    "Furs": {
        "id": 11,
        "base_price": 176,
        "econ_factor": -9,
        "unit": "t",
        "base_quantity": 220,
        "mask": 0b00111111,  # 63
        "string": "Furs",
    },
    "Minerals": {
        "id": 12,
        "base_price": 32,
        "econ_factor": -1,
        "unit": "t",
        "base_quantity": 53,
        "mask": 0b00000011,  # 3
        "string": "Minerals",
    },
    "Gold": {
        "id": 13,
        "base_price": 97,
        "econ_factor": -1,
        "unit": "kg",
        "base_quantity": 66,
        "mask": 0b00000111,  # 7
        "string": "Gold",
    },
    "Platinum": {
        "id": 14,
        "base_price": 171,
        "econ_factor": -2,
        "unit": "kg",
        "base_quantity": 55,
        "mask": 0b00011111,  # 31
        "string": "Platinum",
    },
    "Gem-Stones": {
        "id": 15,
        "base_price": 45,
        "econ_factor": -1,
        "unit": "g",
        "base_quantity": 250,
        "mask": 0b00001111,  # 15
        "string": "Gem-Stones",
    },
    "Alien items": {
        "id": 16,
        "base_price": 53,
        "econ_factor": 15,
        "unit": "t",
        "base_quantity": 192,
        "mask": 0b00000111,  # 3
        "string": "Alien items",
    },
}

def get_pricing_and_availability(commodity_name, economy_type, random_factor, gov_type):
    if gov_type <= 1:
        economy_type = economy_type | 2  # Set bit 1 for Anarchy and Feudal 


    commodity = COMMODITIES[commodity_name]
    base_price = commodity["base_price"]
    econ_factor = commodity["econ_factor"]
    base_quantity = commodity["base_quantity"]
    mask = commodity["mask"]
    unit = commodity["unit"]
    
    if unit=="g":
        wt_factor = 1
    elif unit=="kg":
        wt_factor = 1000
    else:
        wt_factor = 1000000

    product= economy_type * econ_factor
    changing = (random_factor & mask)
  

    #Price calculation
    q = base_price + changing + product
    q = q & 0xFF
    price = int(q * 40)/100

    #Availability calculation
    q = base_quantity + changing - product
    q=q& 0xFF
    if q & 0x80:
        q=0
    availability = q & 0x3F
    
    # Special case: Alien items always unavailable
    if commodity_name == "Alien items":
        availability = 0

    return {
        "name": commodity_name,
        "price": price,
        "quantity": availability,
        "unit": unit,
        "wt_factor": wt_factor,
        "string": commodity["string"]}
    


def get_all_market_data(economy_type, random_factor, gov_type):
    results = []
    for name in COMMODITIES:
        result = get_pricing_and_availability(name, economy_type, random_factor, gov_type)
        results.append(result)
    
    return results



EQUIPMENT = {
    "Fuel": {
        "id": 1,
        "price": 2.0,
        "tech_level_required": 0,
        "string": "Fuel",
    },
    "Missile": {
        "id": 2,
        "price": 30.0,
        "tech_level_required": 0,
        "string": "Missile",
    },
    "Large Cargo Bay": {
        "id": 3,
        "price": 400.0,
        "tech_level_required": 0,
        "string": "Large Cargo Bay",
    },
    "E.C.M. System": {
        "id": 4,
        "price": 600.0,
        "tech_level_required": 2,
        "string": "E.C.M. System",
    },
    "Pulse Laser": {
        "id": 5,
        "price": 400.0,
        "tech_level_required": 3,
        "string": "Pulse Laser",
    },
    "Beam Laser": {
        "id": 6,
        "price": 1000.0,
        "tech_level_required": 4,
        "string": "Beam Laser",
    },
    "Fuel Scoops": {
        "id": 7,
        "price": 525.0,
        "tech_level_required": 5,
        "string": "Fuel Scoops",
    },
    "Escape Capsule": {
        "id": 8,
        "price": 1000.0,
        "tech_level_required": 6,
        "string": "Escape Capsule",
    },
    "Energy Bomb": {
        "id": 9,
        "price": 900.0,
        "tech_level_required": 7,
        "string": "Energy Bomb",
    },
    "Extra Energy Unit": {
        "id": 10,
        "price": 1500.0,
        "tech_level_required": 8,
        "string": "Extra Energy Unit",
    },
    "Docking Computer": {
        "id": 11,
        "price": 1500.0,
        "tech_level_required": 9,
        "string": "Docking Computer",
    },
    "Galactic Hyperdrive": {
        "id": 12,
        "price": 5000.0,
        "tech_level_required": 10,
        "string": "Galactic Hyperdrive",
    },
    "Mining Laser": {
        "id": 13,
        "price": 800.0,
        "tech_level_required": 10,
        "string": "Mining Laser"
    },
    "Military Laser": {
        "id": 14,
        "price": 6000.0,
        "tech_level_required": 10,
        "string": "Military Laser",
    }
}      