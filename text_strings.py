# text_strings.py
# Centralized text string dictionary for all user-facing messages.

#Ship equipment strings and commodity item strings are in market.py

import random

from status import MissionStatus


ADJECTIVES1 = ["A FUNNY","A WIERD","AN UNUSUAL","A STRANGE","A PECULIAR"]
ADJECTIVES1_A = ["FUNNY","WIERD","UNUSUAL","STRANGE","PECULIAR"]
ADJECTIVES2 =["KILLER","DEADLY","EVIL","LETHAL","VICIOUS"]
INSULTS = ["SON OF A BITCH","SCOUNDREL","BLACKGUARD","ROGUE","WHORESON BEETLE HEADED FLAP EAR'D KNAVE"]


text_strings = {

#title screen strings
"ELITE": "---- E L I T E ----",
"python_edition"        : "Python Edition",
"load_prompt"           : "Load New Commander (Y) Or Start New Game (N)?",

#game over screen strings
"game_over"             : "---- GAME OVER ----",
"restart_prompt"        : "Press Any Key To Restart",

#info screen strings
#general header and footer strings
"credits"               : "CREDITS",
"Cr"                    : "Cr",
"remaining_capacity"    : "REMAINING CARGO CAPACITY",
"escape_prompt"         : "ESC to exit page",
"product"               : "PRODUCT",
"unit"                  : "UNIT",
"price"                 : "PRICE",
"availability"          : "AVAILABILITY",

#buy cargo strings
"buy_cargo"             : "BUY CARGO",
"enter_amount_of"       : "ENTER AMOUNT OF",
"to_buy"                : "TO BUY",
"not_enough_stock"      : "Not enough stock available",
"not_enough_capacity"   : "Not enough cargo capacity",
"not_enough_credits"    : "Not enough credits",
"purchased"             : "Purchased",
"for"                   : "for",

#sell cargo strings 
"sell_cargo"            : "SELL CARGO",
"cargo"                 : "CARGO",
"empty_hold"            : "Cargo hold is empty",
"enter_amount"          : "ENTER AMOUNT OF",
"to_sell"               : "TO SELL",
"not_enough_cargo"      : "Not enough cargo",
"sold"                  : "Sold",
"of"                    : "of",

#equip ship strings
"equip_ship"            : "EQUIP SHIP",
"enter_location"        : "ENTER LOCATION TO EQUIP",
"locations"             : "F/B/L/R",
"enter_number"          : "ENTER NUMBER OF ITEM TO EQUIP",  
"invalid_number"        : "Invalid equipment number",
"invalid_location"      : "Invalid location! Use F/B/L/R.",  
"equipped"              : "Equipped",
"already_equipped"      : "Already equipped",
"not_enough_credits"    : "Not enough credits to buy",
"fuel_full"             : "Fuel is already full",   
"refueled_ship"         : "Refueled ship for",
"equipped_missile"      : "Equipped missile for",
"all_missiles_present"  : "All Missiles Present",

#galactic chart strings
"galactic_chart"        : "GALACTIC CHART - GALAXY",
"find_system"           : "FIND SYSTEM",
"not_found"              : "not found",

#short range chart strings
"short_range_chart"     : "SHORT RANGE CHART FOR",

#system info strings
"data_on"                : "DATA ON",

#market prices strings
"market_prices"         : "MARKET PRICES",

#status page strings
"commander"             : "COMMANDER",
"present_system"        : "Present System",
"hyperspace_system"     : "Hyperspace System",
"condition"             : "Condition",
"fuel"                  : "Fuel",
"cash"                  : "Cash",
"legal_status"          : "Legal Status",
"rating"                : "Rating",
"equipment"             : "EQUIPMENT",

#inventory page strings
"inventory"             : "INVENTORY",
"light_years"          : "Light Years",
"empty_hold"            : "CARGO HOLD IS EMPTY",    

#system info page strings
"system"                  : "SYSTEM",
"distance"                : "Distance",
"economy"                 : "Economy",
"government"              : "Government",
"tech_level"             : "Tech Level",
"population"              : "Population",
"billion"                : "Billion",
"gross_productivity"       : "Gross Productivity",
"average_radius"            : "Average Radius",
"m_credit"                : "M Cr",
"km"                      : "km",

#mission briefing strings
"mission_briefing"        : "MISSION BRIEFING COMMANDER",
'incoming_message'        : "IMPORTANT INCOMING MESSAGE",
'accept_y_n'              : "DO YOU ACCEPT THE MISSION? (Y/N)",
'mission_accepted'        : "MISSION ACCEPTED. GOOD LUCK, COMMANDER.",
'mission_declined'        : "MISSION DECLINED. MAYBE NEXT TIME, COMMANDER.",
'acknowledge_message'     : "PRESS ANY KEY TO ACKNOWLEDGE",
'mission_complete'         : "MISSION COMPLETE",

'mission_1_brief'         : """Greetings Commander XXXX,
I am Captain YYYY of Her Majesty's Space Navy and I beg a moment of your valuable time.
We would like you to do a little job for us.
The ship you see here is a new model, the Constrictor, equiped with a top secret new shield generator.
Unfortunately it's been stolen.
It went missing from our ship yard on Xeer five months ago and ZZZZ.
Your mission, should you decide to accept it, is to seek and destroy this ship.
You are cautioned that only Military Lasers will penetrate the new shields and that the Constrictor is fitted with an E.C.M.System.
Good luck, Commander.
MESSAGE ENDS""",

'mission1_galaxy0'    : "was last seen at Reesdice",
'mission1_galaxy1'    : "is believed to have jumped to this galaxy",

'mission_2_brief'         : """Attention Commander XXXX,
I am Captain YYYY of Her Majesty's Space Navy. We have need of your services again.
If you would be so good as to go to Ceerdi you will be briefed.
If successful, you will be well rewarded.
MESSAGE ENDS""",

#XEER
"mission1_2"         : "THE CONSTRICTOR WAS LAST SEEN AT REESDICE, COMMANDER.",                 

#REESDICE   
"mission1_3"         :["XXXX LOOKING SHIP LEFT HERE A WHILE BACK. LOOKED BOUND FOR AREXE.", ADJECTIVES1],

#AREXE
"mission1_4"         : ["YEP, XXXX NEW SHIP HAD A GALACTIC HYPERDRIVE FITTED HERE. USED IT TOO.", ADJECTIVES1],

#ERRIUS
"mission1_5"         : ["THIS XXXX SHIP DEHYPED HERE FROM NOWHERE, SUN SKIMMED AND JUMPED. I HEAR IT WENT TO INBIBE.", ADJECTIVES1_A],   

#INBIBE
"mission1_6"         : ["XXXX SHIP WENT FOR ME AT AUSAR. MY LASERS DIDN'T EVEN SCRATCH THE YYYY.", INSULTS],

#AUSAR
"mission1_7"         : "OH DEAR ME YES. A FRIGHTFUL ROGUE WITH WHAT I BELIEVE YOU PEOPLE CALL A LEAD POSTERIOR SHOT UP LOTS OF THOSE BEASTLY PIRATES AND WENT TO USLERI.", 

#USLERI
"mission1_8"         : ["YOU CAN TACKLE THE XXXX YYYY IF YOU LIKE. HE'S AT ORARRA.", ADJECTIVES2, INSULTS],

#RANDOM MESSAGES ABIOUT ERRIUS
"mission1_10"         : ["I HEAR XXXX LOOKING SHIP APPEARED AT ERRIUS.", ADJECTIVES1],
"mission1_11"        : ["YEAH, I HEAR XXXX SHIP LEFT ERRIUS A WHILE BACK.", ADJECTIVES1],
"mission1_12"        : "GET YOUR IRON ASS OVER TO ERRIUS.",
"mission1_13"        : ["SOME XXXX NEW SHIP WAS SEEN AT ERRIUS.",INSULTS],
"mission1_14"        : "TRY ERRIUS",

#XEVEON
"mission1_23"         : "BOY ARE YOU IN THE WRONG GALAXY!",

#ORARRA
"mission1_24"         : ["THERE'S A REAL XXXX PIRATE OUT THERE.", INSULTS],

#CEERDI
"mission2_1"         : """Good day Commander XXXX.
I am Agent Blake of Naval Intellegence.
As you know, the Navy have been keeping the Thargoids off your ass out in deep space for many years now. Well the situation has changed.
Our boys are ready for a push right to the home system of those mothers.
I have obtained the defence plans for their Hive Worlds. The beetles know we've got something but not what. If I transmit the plans to our base on BIRERA they'll intercept the transmission. I need a ship to make the run.
You're elected.
The plans are unipulse coded within this transmission.
You will be paid.
Good luck Commander.
MESSAGE ENDS""",

"mission1_complete"  :"""Congratulations Commander!
There will always be a place for you in Her Majesty's Space Navy.
And maybe sooner than you think...
MESSAGE ENDS""",

"mission2_complete":"""Well done Commander.
You have served us well and we shall remember.
We did not expect the Thargoids to find out about you.
For the moment please accept this Navy Extra Energy Unit as payment.
MESSAGE ENDS""",

"mission_completed"  :"MISSION COMPLETED",

#save/load strings
"save_commander"          : "SAVE COMMANDER",
"name_exists"             : "COMMANDER NAME EXISTS! OVERWRITE? (Y/N)",
"save_as"                 : "SAVE COMMANDER AS",
"overwritten"             : "OVERWRITTEN",
"canceled"                : "SAVE CANCELED.",
"invalid_name"            : "Invalid commander name",
"saved"                   : "SAVED",
"load_commander"          : "LOAD COMMANDER",
"new_restart"             : "NEW COMMANDER (RESTART GAME)",
"starting_new_commander"  : "STARTING NEW COMMANDER...",
"loaded"                  : "LOADED",

#condition strings
"docked"               : "Docked",
"green"                : "Green",
"yellow"               : "Yellow",
"red"                  : "Red",
"unknown"              : "Unknown",

#legal status strings
"clean"                : "Clean",
"offender"             : "Offender",
"fugitive"             : "Fugitive",

#rating strings
"harmless"             : "Harmless",
"mostly_harmless"      : "Mostly Harmless",
"poor"                 : "Poor",
"average"              : "Average",
"above_average"        : "Above Average",
"competent"            : "Competent",
"dangerous"            : "Dangerous",
"deadly"               : "Deadly",
"elite"                : "---Elite---",

#input related text strings
"abort_jump"            : "Ship in radar range: Jump aborted.",
"station_too_close"     : "Station too close for jump",
"no_computer"           : "No docking computer fitted",
"no_ecm"                : "No ECM System fitted",
"ecm_activated"         : "ECM System Activated",
"targeting_on"          : "Missile Targeting ON",
"targeting_off"         : "Missile Targeting OFF",
"no_missiles"           : "No Missiles Available",
"missile"               : "Missile",
"launched"              : "Launched",
"escape_pod"            : "Escape Pod Launched",
"energy_bomb"           : "Energy Bomb Activated",
"galactic_hyperspace"   : "GALACTIC Hyperspace countdown",
"no_galactic"           : "GALACTIC hyperdrive not installed",
"hyperspace_countdown"  : "Hyperspace countdown to",
"hyperspace_range"      : "Hyperspace Range?",
"no_target_selected"    : "No Target Selected",
"docking_inactive"      : "Docking Computer: INACTIVE",
"docking_active"        : "Docking Computer: ACTIVE",
"docking_too_close_turn": "Docking Computer: TOO CLOSE - TURNING AROUND",
"docking_too_close_away": "Docking Computer: TOO CLOSE - MOVING AWAY",
"docking_turn_to_face"  : "Docking Computer: TURNING TO FACE STATION",
"docking_align(roll)"   : "Docking Computer: ALIGNING WITH TURNING POINT (ROLL)",
"docking_align(pitch)"  : "Docking Computer: ALIGNING WITH TURNING POINT (PITCH)",
"docking_move_to_wp"    : "Docking Computer: MOVING TO TURNING POINT",
"docking_portal(roll)"  : "Docking Computer: ALIGNING WITH PORTAL (ROLL)",
"docking_portal(pitch)" : "Docking Computer: ALIGNING WITH PORTAL (PITCH)",
"docking_portal(move)"  : "Docking Computer: MOVING TO PORTAL",
"docking_final(roll)"   : "Docking Computer: FINAL ALIGNMENT (ROLL)",
"docking_final(pitch)"  : "Docking Computer: FINAL ALIGNMENT (PITCH)",
"docking_final(horiz)"  : "Docking Computer: FINAL HORIZONTAL ALIGNMENT",
"docking_spin_match"    : "Docking Computer: SPIN MATCHING AND DOCKING" ,
"docking_abort"         : "HOSTILE STATION DOCKING ABORTED",    
"docking_complete"      : "Docking Computer: DOCKING COMPLETE",

#view direction strings
"FRONT"                 : "FRONT VIEW",
"BACK"                  : "BACK VIEW",
"LEFT"                  : "LEFT VIEW",
"RIGHT"                 : "RIGHT VIEW",     

#Misc strings
"welcome"               : "Welcome to",
"destroyed"             : "destroyed",
"too_fast"              : "Speed too high for docking",
"not_within_30"         : "Not within 30 degrees of portal",
"outside_portal"        : "Outside of docking portal",
"not_aligned"           : "Ship not aligned horizontally with portal",
"successful"            : "Docking successful.",
"hit_by_hostile"        : "Hit by hostile missile",
"collision_with"        : "Collision with",
"added"                 : "added to Cargo Inventory",
"full"                  : "Cargo hold full, no room for scooped item",
"locked_on"             : "Missile locked on",
"target_lost"           : "Missile target lost",
"hostile_launched"      : "Hostile Missile Launched",
"low_altitude"          : "WARNING: Low altitude",
"high_temp"             : "WARNING: High cabin temperature",
"fuel_scooping"         : "Fuel scooping",
"right_on"              : "RIGHT ON COMMANDER !!",
"bounty_collected"      : "Bounty collected",
"too_near_planet"       : "Jump endpoint too close to planet! (altitude",
"too_near_sun"          : "Jump endpoint too close to sun! (altitude",
"target_lost"           : "Missile target lost",
"self_ECM"              : "Missile jammed by ECM",
"enemy_ECM"             : "Enemy missile jammed by ECM",
"too_close_to_blast"    : "Too close to missile blast"



}

# (galaxy_number, system_number, mission_number): token
SYSTEM_TOKEN_TABLE = {
    (0, 150, 1): 2,   # Xeer
    (0, 36,  1): 3,   # Reesdice
    (0, 28,  1): 4,   # Arexe
    (1, 253, 1): 5,   # Errius
    (1, 79,  1): 6,   # Inbibe
    (1, 53,  1): 7,   # Ausar
    (1, 118, 1): 8,   # Usleri
    (1, 32,  1): 10,  # Bebege
    (1, 68,  1): 11,  # Cearso
    (1, 164, 1): 12,  # Dicela
    (1, 220, 1): 13,  # Eringe
    (1, 106, 1): 14,  # Gexein
    (1, 16,  1): 15,  # Isarin
    (1, 162, 1): 16,  # Letibema
    (1, 3,   1): 17,  # Maisso
    (1, 107, 1): 18,  # Onen
    (1, 26,  1): 19,  # Ramaza
    (1, 192, 1): 20,  # Sosole
    (1, 184, 1): 21,  # Tivere
    (1, 5,   1): 22,  # Veriar
    (2, 101, 1): 23,  # Xeveon
    (1, 193, 1): 24,  # Orarra
    (2, 83,  2): 1,  # Ceerdi - mission 2: 2nd briefing
   
}


def get_text(string_id):
    """Retrieve a text string by its ID. Returns the ID if not found."""
    return text_strings.get(string_id, "not found")

def get_mission_briefing_text(player):
    #get mission 1 briefing text template
    if player.mission_number == 1:
        string = get_text("mission_1_brief")
        if player.galaxy_number == 0:
            galaxy_text = get_text("mission1_galaxy0")
        else:
            galaxy_text = get_text("mission1_galaxy1")
        string = string.replace("ZZZZ", galaxy_text)    
    else:
        string = get_text("mission_2_brief")
    
    #add player name
    string=string.replace("XXXX", player.name) 

    #add navy captain name (changes between Galaxy 0 and Galaxy 1)
    if player.galaxy_number==0:
        captain = "Carruthers"
    elif player.galaxy_number==1:        
        captain = "Captain Fosdyke Smythe"
    else:
        captain = "Fortesque"
    string = string.replace("YYYY", captain)
       
    return string

def check_mission_message(player):
    if player.mission_status != MissionStatus.IN_PROGRESS and player.mission_status != MissionStatus.GOT_PLANS:
        return None
    galaxy_number = player.galaxy_number
    system_number = player.current_system.number
    mission_number = player.mission_number
    token = SYSTEM_TOKEN_TABLE.get((galaxy_number, system_number, mission_number))
    return token
    


def get_mission_message(player):
    token = check_mission_message(player)
    if token is None:
        return None

    if token >=10 and token <=22:
        token = random.randint(10,14)

    message_ID = "mission"+str(player.mission_number)+"_"+str(token)
    
    
    message = get_text(message_ID)
    if isinstance(message, str):
        if player.mission_number == 2:
            message = message.replace("XXXX", player.name)
        return message
    elif isinstance(message, list):
        template = message[0]
        options = message[1]
        option1, option2 = random.sample(options, 2)
        if len(message) == 3:
            option2 = random.choice(message[2])

        return template.replace("XXXX", option1).replace("YYYY", option2)
     