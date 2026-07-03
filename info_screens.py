import status
import math
from status import ship_data,player, global_flags, LaserLocation, LaserType,FONTS, MissileStatus, MissionStatus
from market import EQUIPMENT
import numpy as np
import ogl_render
from OpenGL.GL import (
    glBegin, glEnd, glVertex2f, glColor3f, glColor4f, glLineWidth, glEnable,
    GL_LINE_LOOP, GL_LINES, GL_TRIANGLE_FAN, glPointSize, GL_POINTS, GL_POINT_SMOOTH
)
import os
from text_strings import get_text,get_mission_briefing_text, check_mission_message, get_mission_message
import game_events
class IncomingMessage:
    message=" "


def render_frame_and_header(WIDTH, HEIGHT, header, margin=50):
    
    left = margin
    right = WIDTH - margin
    top = margin
    bottom = HEIGHT*0.8 - margin
    header_height = 40
    glColor3f(1, 1, 1)
    glBegin(GL_LINE_LOOP)
    glVertex2f(left, top)
    glVertex2f(right, top)
    glVertex2f(right, bottom)
    glVertex2f(left, bottom)
    glEnd()
    glBegin(GL_LINE_LOOP)
    glVertex2f(left, top + header_height)
    glVertex2f(right, top + header_height)
    glEnd()

    # --- Draw header centered at top ---

    font = FONTS["header"]
    #text_width, text_height = font.size(header)
    header_x = 0
    header_y = top + 30
    ogl_render.drawText(header_x, header_y,WIDTH,HEIGHT, header, font, text_color=(255,255,255,255), bg_color=(0,0,0,255),centered=True)
    

def draw_wrapped_text(draw_func, text, font, x, y, max_width, line_height, WIDTH, HEIGHT, *args, **kwargs):
    paragraphs = text.split('\n')
    for para in paragraphs:
        words = para.split()
        line = ""
        for word in words:
            test_line = f"{line} {word}".strip()
            width, _ = font.size(test_line)
            if width > max_width and line:
                draw_func(x, y, WIDTH, HEIGHT, line, font, *args, **kwargs)
                y += line_height
                line = word
            else:
                line = test_line
        if line:
            draw_func(x, y, WIDTH, HEIGHT, line, font, *args, **kwargs)
            y += line_height
        # Add extra line for paragraph break
        if para != paragraphs[-1]:
            y += line_height/3


def calculate_distance(sys1, sys2):
    dx = sys2.x - sys1.x
    dy = sys2.y - sys1.y
    distance_ly = np.sqrt(dx**2 + dy**2)*0.4  # Each unit is 0.4 light years
    return math.floor(distance_ly*10)/10


#Info page 1: Buy Cargo
def render_buy_cargo_page(WIDTH, HEIGHT, input):
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, get_text("buy_cargo"), margin=margin)

    font= FONTS["body"]
    margin = 60
    y = margin + 80
    x = margin + 100
    spacer = 22

    show_escape_to_exit(WIDTH, HEIGHT, font)

    remaining_capacity=get_remaining_cargo_capacity()

    market_data = player.market_data
    current_index = getattr(input, "market_index", 0)
    if current_index >= len(market_data):
        player.info_screen_page =9
        return

    display_market_header(x,y,WIDTH,HEIGHT,font)
    y += spacer

    for index in range(current_index+1):
        display_market_item(market_data[index], x, y, WIDTH, HEIGHT, font)
        y += spacer

    y=HEIGHT*0.8 - margin - 40
    ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('enter_amount_of')} {market_data[current_index]['name'].upper()} {get_text('to_buy')}: {input.market_input}", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))

    if input.market_check:
        if input.market_input=="":
            input.market_index+=1
            input.market_check = False  # Reset after processing
        else:
            if int(input.market_input) >market_data[current_index]['quantity']:
                status.add_message(get_text("not_enough_stock"), duration=3, type=0)
                input.market_check = False  # Reset after processing
                input.market_input = ""
            elif int(input.market_input)*market_data[current_index]['wt_factor'] > remaining_capacity:
                status.add_message(get_text("not_enough_capacity"), duration=3, type=0)
                input.market_check = False  # Reset after processing
                input.market_input = ""
            elif int(input.market_input)*market_data[current_index]['price'] > player.credits:
                status.add_message(get_text("not_enough_credits"), duration=3, type=0)
                input.market_check = False  # Reset after processing
                input.market_input = ""
            else:
                # Process the purchase
                total_cost = int(input.market_input) * market_data[current_index]['price']
                total_cost = math.floor(total_cost * 10) / 10  # Round to 1 decimal place
                player.credits -= total_cost
                status.add_message(f"{get_text('purchased')} {market_data[current_index]['name']} {get_text('for')} {total_cost} {get_text('Cr')}", duration=3, type=0)
                # Update cargo inventory
                found = False
                for item in player.cargo_inventory:
                    if item['name'] == market_data[current_index]['name']:
                        item['quantity'] += int(input.market_input)
                        found = True
                        break
                if not found:
                    player.cargo_inventory.append({
                        'name': market_data[current_index]['name'],
                        'quantity': int(input.market_input),
                        'unit': market_data[current_index]['unit'],
                        'wt_factor': market_data[current_index]['wt_factor']
                    })
                # Update market data availability
                market_data[current_index]['quantity'] -= int(input.market_input)
                # Update inventory weight
                player.inventory_weight += int(input.market_input) * market_data[current_index]['wt_factor']
                
                # Reset input for next item
                input.market_input = ""
                input.market_check = False  # Reset after processing
                input.market_index += 1

  

    show_credits(margin, WIDTH,HEIGHT, font)
    show_remaining_cargo_capacity(margin, WIDTH,HEIGHT, font)
    
    
#Info page 2: Sell Cargo
def render_sell_cargo_page(WIDTH, HEIGHT, input):
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, f"{get_text('sell_cargo')}", margin=margin)

    font = FONTS["body"]
    margin = 60
    y = margin + 80
    x = margin + 100
    spacer = 22

    show_escape_to_exit(WIDTH, HEIGHT, font)

    ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('product')}", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
    ogl_render.drawText(x+140,y, WIDTH,HEIGHT, f"{get_text('cargo')}", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
    ogl_render.drawText(x+250, y, WIDTH,HEIGHT, f"{get_text('price')}", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
    y += spacer

    current_index = getattr(input, "market_index", 0)
    if len(player.cargo_inventory) == 0:
        status.add_message(get_text("empty_hold"), duration=3, type=0)
        player.info_screen_page = 9
        return

    if current_index >= len(player.cargo_inventory):
        player.info_screen_page = 9
        return

    local_price=0
    for index in range(current_index+1):
        item = player.cargo_inventory[index]
        
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{item['name']}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
        
        quantity_str=str(item['quantity'])+item['unit']
        if len(quantity_str)<3:
            x_adj=10
        else:
            x_adj=0
        ogl_render.drawText(x+150+x_adj, y, WIDTH,HEIGHT, f"{quantity_str}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
        
        local_price = get_price_by_name(player.market_data, item['name'])
        price_str = str(local_price)
        if len(price_str)<4:
            x_adj=10
        else:
            x_adj=0
        ogl_render.drawText(x+260+x_adj, y, WIDTH,HEIGHT, f"{local_price} {get_text('Cr')}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))

        y += spacer

    y=HEIGHT*0.8-margin-40
    ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('enter_amount')} {player.cargo_inventory[current_index]['name'].upper()} {get_text('to_sell')}: {input.market_input}", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))

    if input.market_check:
        if input.market_input=="":
            input.market_index+=1
            input.market_check = False  # Reset after processing
        else:

            if int(input.market_input) >player.cargo_inventory[current_index]['quantity']:
                status.add_message(get_text("not_enough_cargo"), duration=3, type=0)
                input.market_check = False  # Reset after processing
                input.market_input = ""
            else:
                sell_quantity=int(input.market_input)
                local_price = get_price_by_name(player.market_data, player.cargo_inventory[current_index]['name'])
                total_revenue = int(sell_quantity) * local_price
                total_revenue = math.floor(total_revenue * 10) / 10  # Round to 1 decimal place
                player.credits += total_revenue
                status.add_message(f"{get_text('sold')} {sell_quantity}{player.cargo_inventory[current_index]['unit']} {get_text('of')} {player.cargo_inventory[current_index]['name']} {get_text('for')} {total_revenue} {get_text('Cr')}", duration=3, type=0)
                # Update cargo inventory
                player.cargo_inventory[current_index]['quantity'] -= sell_quantity
                
                # Update market data availability
                for market_item in player.market_data:
                    if market_item['name'] == player.cargo_inventory[current_index]['name']:
                        market_item['quantity'] += sell_quantity
             
                # Reset input for next item
                player.inventory_weight -= sell_quantity * player.cargo_inventory[current_index]['wt_factor']

                if player.cargo_inventory[current_index]['quantity'] == 0:
                    del player.cargo_inventory[current_index]
                    input.market_index -= 1  # Adjust index since we removed an item

            input.market_input = ""
            if input.market_index < len(player.cargo_inventory)-1:
                input.market_index += 1
            input.market_check = False  # Reset after processing


    show_credits(margin, WIDTH,HEIGHT, font)
    show_remaining_cargo_capacity(margin, WIDTH,HEIGHT, font)


#Info page 3:Equip Ship
def render_equip_ship_page(WIDTH, HEIGHT, input):
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, f"{get_text('equip_ship')}", margin=margin)

    font = FONTS["body"]
    margin = 60
    y = margin + 80
    x = margin + 100
    spacer = 22

    show_escape_to_exit(WIDTH, HEIGHT, font)

    tech_level = player.current_system.tech_level
    i=1
    for item in EQUIPMENT:
        if tech_level >= EQUIPMENT[item]['tech_level_required']:
            ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{i}. {EQUIPMENT[item]['string']}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
            
            if item == "Fuel":
                price_str = str(EQUIPMENT[item]['price'] * (70-ship_data.fuel_level)/10)
            else:
                price_str = str(EQUIPMENT[item]['price'])
            
            x_adj = 10*(6-len(price_str))

            ogl_render.drawText(x+300+x_adj, y, WIDTH,HEIGHT, f"{price_str}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
            y += spacer
            i+=1

    y=y=HEIGHT*0.8 - margin - 40
    
    if input.get_laser_location:
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('enter_location')} {input.laser_to_equip.upper()} ({get_text('locations')}): {input.market_input}", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
    else:
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('enter_number')}: {input.market_input}", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
    
    
    if input.market_check:
        if input.get_laser_location:
            process_laser_addition(input.laser_to_equip, input.market_input)
            input.get_laser_location = False
            input.market_input = ""
            input.laser_to_equip = ""
        else:
            name = get_equipment_by_id(EQUIPMENT, int(input.market_input))
            if name != "NOT FOUND" and tech_level >= EQUIPMENT[name]['tech_level_required']:
                if name == "Fuel":
                    cost = EQUIPMENT[name]['price'] * (70-ship_data.fuel_level)/10
                    if check_credits(cost,name):
                        process_fuel_addition(cost)
                        
                elif name == "Missile":
                    cost = EQUIPMENT[name]['price']
                    if check_credits(cost,name):
                            process_missile_addition(cost)
                elif name == "Pulse Laser" or name == "Beam Laser" or name == "Military Laser" or name == "Mining Laser":
                    input.get_laser_location = True
                    input.laser_to_equip = name
                else: 
                    cost = EQUIPMENT[name]['price']
                    if check_credits(cost,name):
                        process_generic_equipment_addition(name,cost)

            else:
                status.add_message(get_text("invalid_number"), duration=3, type=0)    

        input.market_input = ""
        input.market_check = False  # Reset after processing

    show_credits(margin, WIDTH,HEIGHT, font)
    

#Info page 4: Galactic chart
def render_galactic_chart(WIDTH, HEIGHT, input):
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, f"{get_text('galactic_chart')} {player.galaxy_number+1}", margin=margin)

    all_systems = player.all_systems
    current_system = player.current_system
    margin = 50
    chart_left = margin*3
    chart_top = margin*2
    
    if global_flags.FULLSCREEN:
        chart_width = WIDTH*0.8 - 5.5 * margin
    else:
        chart_width = WIDTH*0.9 - 5.5 * margin

    chart_height=chart_width/2
    # Find min/max x/y for scaling
    xs = [sys.x for sys in all_systems]
    ys = [sys.y for sys in all_systems]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    # Avoid division by zero
    range_x = max(1, max_x - min_x)
    range_y = max(1, max_y - min_y)

    #draw system dots
    for sys in all_systems:
        px = chart_left + int((sys.x - min_x) / range_x * chart_width)
        py = chart_top + int((sys.y - min_y) / range_y * chart_height)
        size_map = {1: 4, 2: 8, 3: 12}
        dot_size = size_map.get(sys.longRangeSize, 6)
        draw_dots(px, py, (1,1,1,0.8), dot_size)
        
    # Draw crosshair and fuel circle at player's current system position
    player_x = player.current_system.x
    player_y = player.current_system.y
    cross_px = chart_left + int((player_x - min_x) / range_x * chart_width)
    cross_py = chart_top + int((player_y - min_y) / range_y * chart_height)
    
    color = (1, 1, 1, 1)
    draw_cross_hairs(cross_px, cross_py, color, size=10)

    # Draw fuel range circle
    fuel_radius_ly = getattr(ship_data, 'fuel_level', 0) / 10
    pixel_scale = chart_width / 256
    draw_fuel_circle(cross_px, cross_py, fuel_radius_ly, pixel_scale)

    ogl_render.drawText(chart_left + 10, chart_top + chart_height + 60, WIDTH,HEIGHT, f"{get_text('find_system')}: {input.find_system_input}", FONTS['body'], text_color=(255,255,255,255), bg_color=(0,0,0,0))   

    if input.find_system:
        found=False
        for system in all_systems:
            if system.name.lower() == input.find_system_input.lower():
                found=True
                player.galaxy_selected_system = system
                player.galaxy_distance_to_selected = calculate_distance(current_system, player.galaxy_selected_system)
                player.galactic_xy = (system.x, system.y)
                break
        if not found:
            status.add_message(f"{input.find_system_input} {get_text('not_found')}", duration=3, type=0)
        input.find_system_input = ""
        input.find_system = False

    #draw mobile crosshairs
    crosshair_x = chart_left + int((player.galactic_xy[0] - min_x) / range_x * chart_width)
    crosshair_y = chart_top + int((player.galactic_xy[1] - min_y) / range_y * chart_height)

    player.galactic_xy=check_cross_hairs_within_bounds(crosshair_x, crosshair_y, chart_left, chart_top, chart_width, chart_height,player.galactic_xy)   
    
    color = (0, 1, 0, 1)
    draw_cross_hairs(crosshair_x, crosshair_y, color, size=15)

    # Find closest system to crosshair
    closest_system_index=current_system.number
    min_distance = float('inf')
    for sys in all_systems:
        cross_dx = sys.x - player.galactic_xy[0]
        cross_dy = sys.y - player.galactic_xy[1]
        dist = (cross_dx**2 + cross_dy**2) ** 0.5
        if dist < min_distance:
            min_distance = dist
            closest_system_index = sys.number

    player.galaxy_selected_system = all_systems[closest_system_index]
    player.galaxy_distance_to_selected = calculate_distance(current_system, player.galaxy_selected_system)

    # Draw selected system info box
    x=WIDTH-550
    y=chart_top + chart_height + 25
    spacer=14
    font = FONTS['small']
    
    if player.current_system != player.galaxy_selected_system:
        distance = player.galaxy_distance_to_selected
    else:
        distance = 0

    display_system_info(player.galaxy_selected_system, distance, x, y, WIDTH, HEIGHT, font, spacer, wrap_width=500)

    return


#Info page 5: Short Range Chart
def render_short_range_chart(WIDTH, HEIGHT):
    current_system = player.current_system
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, f"{get_text('short_range_chart')} {current_system.name.upper()}", margin=margin)

    all_systems = player.all_systems
    current_x, current_y = current_system.x, current_system.y
    chart_width = WIDTH//2*0.7
    chart_left = WIDTH//2 - chart_width//2-margin*4
    chart_top = (HEIGHT*0.8)//2 - chart_width//2
    chart_height = chart_width
    pixel_scale = chart_width / 38

    # Precompute chart center
    center_x = chart_left + chart_width//2
    center_y = chart_top + chart_height//2

    # Draw fuel range circle
    radius = getattr(ship_data, 'fuel_level', 0) / 10
    draw_fuel_circle(center_x, center_y, radius, pixel_scale)
    
    # Pre-create font
    font = FONTS['body']
    closest_system_index = current_system.number
    min_distance = float('inf')

    # Filter systems within chart bounds
    nearby_systems = [sys for sys in all_systems if abs(sys.x - current_x) < 20 and abs(sys.y - current_y) < 18]

    for sys in nearby_systems:
        dx = sys.x - current_x
        dy = sys.y - current_y
        cross_dx = sys.x - player.short_range_xy[0]
        cross_dy = sys.y - player.short_range_xy[1]
        dist = (cross_dx**2 + cross_dy**2) ** 0.5
        if dist < min_distance:
            min_distance = dist
            closest_system_index = sys.number

        px = center_x + int(dx * pixel_scale)
        py = center_y + int(dy * pixel_scale)
        size_map = {2: 3, 3: 6, 4: 9}
        dot_size = size_map.get(sys.shortRangeSize, 4)
        color = (0,1,0,1) if sys.number == current_system.number else (1,1,1,1)

        draw_dots(px, py, color, dot_size*2)
        ogl_render.drawText(px+dot_size+2, py, WIDTH, HEIGHT, sys.name.capitalize(), font, text_color=(255,255,255), bg_color=(0,0,0))

    # Draw crosshair
    crosshair_x = center_x + int((player.short_range_xy[0]-current_x) * pixel_scale)
    crosshair_y = center_y + int((player.short_range_xy[1]-current_y) * pixel_scale)
    
    # Clamp crosshair to chart bounds
    player.short_range_xy=check_cross_hairs_within_bounds(crosshair_x, crosshair_y, chart_left, chart_top, chart_width, chart_height,player.short_range_xy)

    color = (0, 1, 0, 1)
    draw_cross_hairs(crosshair_x, crosshair_y,color,15)

    player.selected_system = all_systems[closest_system_index]
    player.distance_to_selected = calculate_distance(current_system, player.selected_system)

    font = FONTS["body"]
    margin = 60
    y = chart_top + 80
    x = chart_left + chart_width + 120
    spacer = 25

    if player.current_system != player.selected_system:
        distance = player.distance_to_selected
    else:
        distance = 0

    display_system_info(player.selected_system, distance, x, y, WIDTH, HEIGHT, font, spacer, wrap_width=350)


#Info page 6: System Data
def render_system_data(WIDTH, HEIGHT,input,main_loop_counter):
    
    #this is the first screen after docking, so check for mission status to determine if we show briefing, extra mission text, or just system data
    mission_status_checker(input)
    if player.mission_status == MissionStatus.BRIEFING:
        player.info_screen_page=12
        global_flags.accept_input = False
        return

    if player.mission_status == MissionStatus.SUCCESS:
        player.info_screen_page=14
        global_flags.accept_input = False
        return
    
    
    message_to_display = check_mission_message(player)
    if message_to_display and not global_flags.message_seen:
        player.info_screen_page=13
        global_flags.frame_start=main_loop_counter
        global_flags.accept_input = False
        global_flags.message_refresh = False
        IncomingMessage.message = get_mission_message(player) or ""
        return
    elif message_to_display and global_flags.message_refresh:
        global_flags.message_refresh = False
        IncomingMessage.message = get_mission_message(player) or ""
    elif not message_to_display:
        IncomingMessage.message = ""


    #ok, now we can show the system data screen if we haven't already shown the briefing or extra mission text
    system_data = player.selected_system
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, f"{get_text('data_on')} {getattr(system_data, 'name', 'SYSTEM').upper()}", margin=margin)

    # --- Draw system data fields ---
    font = FONTS["body"]
    margin = 60
    y = margin + 80
    x = margin + 100
    spacer = 25
    
    if player.current_system != player.selected_system:
        distance = player.distance_to_selected
    else:
        distance = 0

    display_system_info(player.selected_system, distance, x, y, WIDTH, HEIGHT, font, spacer, wrap_width=WIDTH - 5*margin)


#Info page 7: Market Prices
def render_market_prices(WIDTH, HEIGHT):
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, f"{player.current_system.name.upper()} {get_text('market_prices')}", margin=margin)

    font=FONTS["body"]
    margin = 60
    y = margin + 80
    x = margin + 100
    spacer = 22

    display_market_header(x,y,WIDTH,HEIGHT,font)
    y += spacer

    for item in player.market_data:
        display_market_item(item,x,y,WIDTH,HEIGHT,font)
        y += spacer


#Info page 8: Status Page
def render_status_page(WIDTH, HEIGHT,objectList):
    current_system = player.current_system
    selected_system = player.selected_system
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, f"{get_text('commander')} {getattr(player, 'name', 'UNKNOWN').upper()}", margin=margin)

    # --- Draw system data fields ---
    font= FONTS["body"]
    margin = 60
    y = margin + 80
    x = margin + 100
    spacer = 25

    status_fields = [
        (get_text("present_system"), lambda: current_system.name),
        (get_text("hyperspace_system"), lambda: selected_system.name),
        (get_text("condition"), lambda: get_condition(objectList)),
        (get_text("fuel"), lambda: f"{ship_data.fuel_level/10:.1f} {get_text('light_years')}"),
        (get_text("cash"), lambda: f"{player.credits:.1f} {get_text('Cr')}"),
        (get_text("legal_status"), get_legal_status),
        (get_text("rating"), get_rating),
    ]
    for label, value_fn in status_fields:
        ogl_render.drawText(x, y, WIDTH, HEIGHT, label, font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
        ogl_render.drawText(x+200, y, WIDTH, HEIGHT, f": {value_fn()}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
        y += spacer
    
    ogl_render.drawText(x, y, WIDTH, HEIGHT, f"{get_text('equipment')}: ", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
    y += (spacer-5)

    equipment_display_map = {
        "Large Cargo Bay": "large_cargo_bay",
        "E.C.M. System": "ECM_System",
        "Fuel Scoops": "fuel_scoops",
        "Escape Capsule": "escape_capsule",
        "Energy Bomb": "energy_bomb",
        "Extra Energy Unit": "extra_energy_unit",
        "Naval Extra Energy Unit": "navy_energy_unit",
        "Docking Computer": "docking_computer",
        "Galactic Hyperdrive": "galactic_hyperdrive",
    }
    for display_name, attr in equipment_display_map.items():
        if getattr(ship_data, attr, False):
            ogl_render.drawText(x+50, y, WIDTH, HEIGHT, display_name, font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
            y += (spacer-5)

    for loc in LaserLocation:
        # guard in case ship_data.lasers is shorter than expected
        try:
            laser_type = ship_data.lasers[loc.value]
        except IndexError:
            continue

        if laser_type != LaserType.NOT_PRESENT:
            ogl_render.drawText(x+50, y, WIDTH,HEIGHT, f"{loc.name.capitalize()} {laser_type.name.capitalize()} Laser", font, text_color=(255,255,255,255), bg_color=(0,0,0,0)); y += (spacer-5)


#Info page 9: Inventory
def render_inventory_page(WIDTH, HEIGHT):
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, f"{get_text('inventory')}", margin=margin)

    font= FONTS["body"]
    margin = 60
    y = margin + 80
    x = margin + 100
    spacer = 25

    ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('fuel')}: {ship_data.fuel_level/10:.1f} {get_text('light_years')}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
    y+=spacer
    ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('cash')}: {player.credits:.1f} {get_text('Cr')}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))

    y += spacer
    y+=spacer

    if len(player.cargo_inventory)==0:
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('empty_hold')}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
        return
    for item in player.cargo_inventory:
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{item['name']}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
        
        quantity_str=str(item['quantity'])+item['unit']      
        if len(quantity_str)<3:
            x_adj=10
        else:
            x_adj=0

        ogl_render.drawText(x+220+x_adj, y, WIDTH,HEIGHT, f"{quantity_str}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
        y += spacer


#info page 10: save game
def render_save_game_page(WIDTH, HEIGHT, input):
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, f"{get_text('save_commander')} {player.name.upper()}", margin=margin)

    # --- Draw system data fields ---
    font = FONTS["body"]
    margin = 60
    y = margin + 80
    x = margin + 100
    spacer = 25
    
    show_escape_to_exit(WIDTH, HEIGHT, font)
    
    y=560

    if input.overwrite_check:
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('name_exists')}", font, text_color=(255,0,0,255), bg_color=(0,0,0,0))
    else:    
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('save_as')}:", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
        ogl_render.drawText(x+200, y, WIDTH,HEIGHT, f"{input.market_input}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))

    if input.overwrite_check:
        if input.market_input == 'Y':
            player.name=input.filename[6:-5]  # Extract name from filename
            status.save_game_to_json(input.filename)
            status.add_message(f"{get_text('commander')} {input.filename[6:-5]} {get_text('overwritten')}", duration=3, type=0)
            input.market_input = ""
            input.overwrite_check = False
            player.info_screen_page = 8
            

        elif input.market_input == 'N':
            status.add_message(f"{get_text('canceled')}", duration=3, type=0)
            input.market_input = ""
            input.overwrite_check = False
            player.info_screen_page = 8
        
        return

    if input.market_check:
        if input.market_input=="":
            input.filename = ""
            status.add_message(get_text("invalid_name"), duration=3, type=0)
        elif input.market_input in get_saved_game_names():
            input.overwrite_check = True
            input.filename = f"saves/{input.market_input}.json"
        else:
            input.filename = f"saves/{input.market_input}.json"
            player.name=input.filename[6:-5]  # Extract name from filename
            status.save_game_to_json(input.filename)
            status.add_message(f"{get_text('commander')} {input.filename[6:-5]} {get_text('saved')}", duration=3, type=0)
            player.info_screen_page = 8
           
        input.market_input = ""
        input.market_check = False  # Reset after processing
        

    return

#info page 11: load game
def render_load_game_page(WIDTH, HEIGHT, input):
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, get_text('load_commander'), margin=margin)

    # --- Draw system data fields ---
    font = FONTS["body"]
    margin = 60
    y = margin + 80
    x = margin + 100
    spacer = 25
    
    show_escape_to_exit(WIDTH, HEIGHT, font)

    file_list = get_saved_game_names()
    file_list.append(get_text("new_restart"))  #option for new commander

    if input.market_index < 0:
        input.market_index = len(file_list) - 1
    elif input.market_index >= len(file_list):
        input.market_index = 0

    for i, filename in enumerate(file_list):
        if i==input.market_index:
            ogl_render.drawText(x, y, WIDTH,HEIGHT, f">>", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
        
        ogl_render.drawText(x+60, y, WIDTH,HEIGHT, f"{filename}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
        y += spacer

    y = 560
    ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('load_commander')}:", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
    ogl_render.drawText(x+175, y, WIDTH,HEIGHT, f"{file_list[input.market_index]}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))


    if input.market_check:
        selected_file = file_list[input.market_index]
        if selected_file == get_text("new_restart"):
            status.add_message(get_text("starting_new_commander"), duration=3, type=0)
            global_flags.reset_game=True
        else:
            filename = f"saves/{selected_file}.json"
            status.load_game_from_json(filename)
            status.add_message(f"{get_text('commander')} {selected_file} {get_text('loaded')}", duration=3, type=0)
            player.info_screen_page = 8
            player.name=selected_file  # Set player name
            if global_flags.is_title_screen:
                global_flags.game_state = global_flags.STATE_DOCKED

        input.market_check = False  # Reset after processing


#info page 12: mission briefing page
def render_mission_page(WIDTH, HEIGHT,screen_center, main_loop_counter, focal_length):
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, f"{get_text('mission_briefing')} {player.name.upper()}", margin=margin)

    # --- Draw system data fields ---
    font = FONTS["body"]
    margin = 60
    y = margin + 80
    x = margin + 50
    spacer = 25

    if player.mission_number == 1 and player.mission_status == MissionStatus.BRIEFING:
        ogl_render.render_constrictor(screen_center, WIDTH, HEIGHT, main_loop_counter, focal_length)
        
    if show_incoming_message_alert(main_loop_counter, WIDTH, HEIGHT, x, y):
        return

     
    briefing_text= get_mission_briefing_text(player)


    draw_wrapped_text(
                            ogl_render.drawText,
                            briefing_text,
                            font,
                            x, y,
                            max_width=780,
                            line_height=spacer,
                            WIDTH=WIDTH,
                            HEIGHT=HEIGHT,
                            text_color=(255,255,255,255),
                            bg_color=(0,0,0,0)
                        )
    y=y=HEIGHT*0.8-margin-20

    ogl_render.drawText(x, y, WIDTH, HEIGHT, f"{get_text('accept_y_n')}", font, text_color=(100,255,100,255), bg_color=(0,0,0,0),centered=True)


    return

# info page 13: incoming mission message
def render_incoming_message_page(WIDTH, HEIGHT, input, main_loop_counter):
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, get_text('incoming_message'), margin=margin)

    # --- Draw system data fields ---
    font=FONTS["header"]
    margin = 60
    y = margin + 200
    x = margin + 100
    spacer = 25

    if show_incoming_message_alert(main_loop_counter, WIDTH, HEIGHT, x, y):
        return

    message_text = IncomingMessage.message or ""

    #reduce font size for the mission 2 mid mission message and move to next phase (that's the only message for mission 2)
    if player.mission_number==2:
        font=FONTS["body"]
        y=margin+75
        

    draw_wrapped_text(
                            ogl_render.drawText,
                            message_text,
                            font,
                            x, y,
                            max_width=700,
                            line_height=spacer,
                            WIDTH=WIDTH,
                            HEIGHT=HEIGHT,
                            text_color=(255,255,255,255),
                            bg_color=(0,0,0,0)
                        )
    y=y=HEIGHT*0.8-margin-20

    ogl_render.drawText(x, y, WIDTH, HEIGHT, f"{get_text('acknowledge_message')}", font, text_color=(100,255,100,255), bg_color=(0,0,0,0),centered=True)

# info page 14: mission complete message
def render_mission_complete_page(WIDTH, HEIGHT, input, main_loop_counter):
    
    if player.mission_status==MissionStatus.SUCCESS:
        game_events.mission_complete_actions()
    
    margin = 50
    render_frame_and_header(WIDTH, HEIGHT, get_text('mission_complete'), margin=margin)

    # --- Draw system data fields ---
    font=FONTS["header"]
    margin = 60
    y = margin + 200
    x = margin + 100
    spacer = 25


    if show_incoming_message_alert(main_loop_counter, WIDTH, HEIGHT, x, y):
        return
 

    message_text = "empty"
    if player.mission_number==1:
        message_text = get_text('mission1_complete')
    elif player.mission_number==2:
        message_text = get_text('mission2_complete')

    draw_wrapped_text(
                            ogl_render.drawText,
                            message_text,
                            font,
                            x, y,
                            max_width=780,
                            line_height=spacer,
                            WIDTH=WIDTH,
                            HEIGHT=HEIGHT,
                            text_color=(255,255,255,255),
                            bg_color=(0,0,0,0)
                        )
    y=y=HEIGHT*0.8-margin-20

    ogl_render.drawText(x, y, WIDTH, HEIGHT, f"{get_text('acknowledge_message')}", font, text_color=(100,255,100,255), bg_color=(0,0,0,0),centered=True)

   

def show_incoming_message_alert(main_loop_counter, WIDTH, HEIGHT, x, y):
    if main_loop_counter < global_flags.frame_start+150:
        font=FONTS["header"]
        y=y+100
        ogl_render.drawText(x, y, WIDTH, HEIGHT, f"{get_text('incoming_message')}", font, text_color=(100,255,100,255), bg_color=(0,0,0,0),centered=True)
        global_flags.alert_on = True
       
    else:
        global_flags.alert_on = False

    return global_flags.alert_on    


def mission_status_checker(input):
    #check if mission already underway
    if player.mission_number ==0:
        #no mission started, check if eligible for mission 1 256 kills and in galaxy 0 or 1
        if player.kills>=256 and player.galaxy_number<=1:
            player.mission_number=1
            player.mission_status=MissionStatus.BRIEFING
    elif player.mission_number ==1 and player.mission_status == MissionStatus.COMPLETED:
        #mission 1 completed, check if eligible for mission 2 1344 kills and in galaxy 2
        if player.kills>=1344 and player.galaxy_number==2:
            player.mission_number=2
            player.mission_status=MissionStatus.BRIEFING
    elif player.mission_number ==2 and player.mission_status == MissionStatus.IN_PROGRESS and player.current_system.number==83 and player.galaxy_number==2:
        player.mission_status=MissionStatus.GOT_PLANS
        for system in player.all_systems:
            if system.name == "BIRERA":
                player.galactic_xy = (system.x, system.y)
                player.selected_system = system
                break
    elif player.mission_number ==2 and player.mission_status == MissionStatus.GOT_PLANS and player.current_system.number==36 and player.galaxy_number==2:
        player.mission_status=MissionStatus.SUCCESS    

    

def get_saved_game_names(market_input=None):
    """
    Returns a list of filenames in the current directory that match the given market_input (case-insensitive) with a .json extension.
    If market_input is None, returns all .json files in the current directory.
    """
    
    files = []
    saves_dir = 'saves'
    if not os.path.isdir(saves_dir):
        return files
    for f in os.listdir(saves_dir):
        if f.lower().endswith('.json'):
            name = f[:-5]  # Remove .json
            files.append(name)
    return files
    

def get_price_by_name(market_data, name):
    for item in market_data:
        if item["name"] == name:
            return item["price"]
    return 0  # or raise an error if not found

def display_market_header(x,y,WIDTH,HEIGHT,font):
    ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('product')}", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
    ogl_render.drawText(x+200,y, WIDTH,HEIGHT, f"{get_text('unit')}", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
    ogl_render.drawText(x+300, y, WIDTH,HEIGHT, f"{get_text('price')}", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
    ogl_render.drawText(x+450, y, WIDTH,HEIGHT, f"{get_text('availability')}", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))

def display_market_item(item,x,y,WIDTH,HEIGHT,font):
    ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{item['string']}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
    ogl_render.drawText(x+220, y, WIDTH,HEIGHT, f"{item['unit']}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
    price_str = str(item['price'])
    if len(price_str)<4:
        x_adj=10
    else:
        x_adj=0
    ogl_render.drawText(x+300+x_adj, y, WIDTH,HEIGHT, f"{price_str}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))
    
    if str(item['quantity'])=='0':
            quantity_str="-"
            x_adj=10
    else:
        quantity_str=str(item['quantity'])+item['unit']      
        if len(quantity_str)<3:
            x_adj=10
        else:
            x_adj=0

    ogl_render.drawText(x+470+x_adj, y, WIDTH,HEIGHT, f"{quantity_str}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))

def display_system_info(system_data, distance, x, y, WIDTH, HEIGHT, font, spacer,wrap_width):
    
    ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('system')}: {system_data.name.upper()}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0)); y += spacer
    
    if distance !=0:
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('distance')}: {distance:.1f} {get_text('light_years')}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0)); y += spacer

    if hasattr(system_data, 'economy'):
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('economy')}: {system_data.prosperity_str} {system_data.economy_str}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0)); y += spacer
    if hasattr(system_data, 'government'):
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('government')}: {system_data.government_str}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0)); y += spacer
    if hasattr(system_data, 'tech_level'):
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('tech_level')}: {system_data.tech_level}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0)); y += spacer
    if hasattr(system_data, 'population'):
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('population')}: {system_data.population} {get_text('billion')}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0)); y += spacer
    if hasattr(system_data, 'speciesType'):
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"({system_data.speciesType})", font, text_color=(255,255,255,255), bg_color=(0,0,0,0)); y += spacer
    if hasattr(system_data, 'grossProductivity'):
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('gross_productivity')}: {system_data.grossProductivity} {get_text('m_credit')}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0)); y += spacer
    if hasattr(system_data, 'averageRadius'):
        ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('average_radius')}: {system_data.averageRadius} {get_text('km')}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0)); y += spacer

    if hasattr(system_data, 'description'):
        draw_wrapped_text(
                            ogl_render.drawText,
                            system_data.description,
                            font,
                            x, y,
                            max_width=wrap_width,
                            line_height=spacer,
                            WIDTH=WIDTH,
                            HEIGHT=HEIGHT,
                            text_color=(255,255,255,255),
                            bg_color=(0,0,0,0)
                        );y += spacer*3
        
    if len(IncomingMessage.message) >0 and player.mission_number!=2:
        draw_wrapped_text(
                            ogl_render.drawText,
                            IncomingMessage.message,
                            font,
                            x, y,
                            max_width=wrap_width,
                            line_height=spacer,
                            WIDTH=WIDTH,
                            HEIGHT=HEIGHT,
                            text_color=(100,255,100,255),
                            bg_color=(0,0,0,0)
                        )


     
def get_condition(objectList):
    if global_flags.is_docked:
        return get_text("docked")
    elif global_flags.is_flying:
        green=True
        green = not any(
            obj.type == 'ship' and obj.distance_to_player < status.game_constants.RADAR_RANGE
            for obj in objectList
        )
        if green:        
            return get_text("green")
        elif ship_data.energy_level < 128:
            return get_text("red")
        else:
            return get_text("yellow")
    return get_text("unknown")

def get_legal_status():
    if player.FIST<1:
        return get_text("clean")
    elif player.FIST<50:
        return get_text("offender")
    else:
        return get_text("fugitive")

def get_rating():
    # Each tuple is (minimum_kills, rating_key)
    ratings = [
        (6144, "elite"),
        (2304, "deadly"),
        (512, "dangerous"),
        (128, "competent"),
        (64, "above_average"),
        (32, "average"),
        (16, "poor"),
        (8, "mostly_harmless"),
        (0, "harmless"),
    ]
    kills = player.kills
    for min_kills, rating_key in ratings:
        if kills >= min_kills:
            return get_text(rating_key)


def get_equipment_by_id(equipment_dict, search_id):
    for name, data in equipment_dict.items():
        if data.get("id") == search_id:
            return name
    return "NOT FOUND"  # Not found

def check_credits(cost,item_name):
    if player.credits >= cost:
        return True
    else:
        status.add_message(f"{get_text('not_enough_credits')} {item_name}", duration=3, type=0)
        return False

def show_credits(margin,WIDTH,HEIGHT, font):
    x= 160
    y=HEIGHT*0.8-margin-20
    ogl_render.drawText(x, y, WIDTH,HEIGHT, f"{get_text('credits')}: ", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
    ogl_render.drawText(x+85, y, WIDTH,HEIGHT, f"{player.credits:.1f} {get_text('Cr')}", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))

def show_remaining_cargo_capacity(margin,WIDTH,HEIGHT, font):
    x= 160
    y=HEIGHT*0.8-margin-20
    remaining_capacity=get_remaining_cargo_capacity()/1000000

    ogl_render.drawText(x+200,y, WIDTH,HEIGHT, f"{get_text('remaining_capacity')}: ", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))
    ogl_render.drawText(x+465,y, WIDTH,HEIGHT, f"{remaining_capacity:.1f} t", font, text_color=(255,255,255,255), bg_color=(0,0,0,0))

def show_escape_to_exit(WIDTH, HEIGHT, font):
    ogl_render.drawText(WIDTH-150, 30, WIDTH,HEIGHT, f"{get_text('escape_prompt')}", font, text_color=(255,255,0,255), bg_color=(0,0,0,0))

def get_remaining_cargo_capacity():
    if ship_data.large_cargo_bay:
        capacity=35000000
    else:
        capacity=20000000

    remaining_capacity=(capacity - player.inventory_weight)
    return remaining_capacity       

def check_laser_affordability(laser_type):
    cost = EQUIPMENT[laser_type]['price']
    trade_in=0
    for loc in LaserLocation:
        value=0
        if ship_data.lasers[loc.value] == LaserType.NOT_PRESENT:
            value=0
        elif ship_data.lasers[loc.value] == LaserType.PULSE:
            value= EQUIPMENT['Pulse Laser']['price']
        elif ship_data.lasers[loc.value] == LaserType.BEAM:
            value= EQUIPMENT['Beam Laser']['price']
        elif ship_data.lasers[loc.value] == LaserType.MILITARY:
            value= EQUIPMENT['Military Laser']['price']
        elif ship_data.lasers[loc.value] == LaserType.MINING:
            value= EQUIPMENT['Mining Laser']['price']
        if value > trade_in:
            trade_in = value

        if player.credits >= cost-trade_in:
            return True
    else:
        status.add_message(f"{get_text('not_enough_credits')} {laser_type}", duration=3, type=0)
        return False

def process_fuel_addition(cost):
    if cost==0:
        status.add_message(get_text("fuel_full"), duration=3, type=0)
        return
    ship_data.fuel_level = 70
    player.credits -= cost
    status.add_message(f"{get_text('refueled_ship')} {cost} {get_text('Cr')}", duration=3, type=0)

def process_missile_addition(cost):
    empty_slot = next((idx for idx, status in enumerate(ship_data.missile_status) if status == MissileStatus.NOT_PRESENT),None)
    if empty_slot is not None:
        ship_data.missile_status[empty_slot] = MissileStatus.PRESENT
        player.credits -= cost
        status.add_message(f"{get_text('equipped_missile')} {cost} {get_text('Cr')}", duration=3, type=0)
    else:
        status.add_message(get_text("all_missiles_present"), duration=3, type=0)    


def process_laser_addition(laser_name, location):
    location_map = {'F': 0, 'B': 1, 'L': 2, 'R': 3}
    location_index = location_map.get(location.upper(), None)
    if location_index is None:
        status.add_message(get_text("invalid_location"), duration=3, type=0)
        return
    
    existing_laser_type = ship_data.lasers[location_index]
    trade_in = 0
    laser_name_map = {LaserType.PULSE: 'Pulse Laser', LaserType.BEAM: 'Beam Laser', LaserType.MILITARY: 'Military Laser', LaserType.MINING: 'Mining Laser'}
    existing_laser_name = laser_name_map.get(existing_laser_type, None)

    if existing_laser_name ==laser_name:
        status.add_message(f"{laser_name} already equipped at that location", duration=3, type=0)
        return
    else:
        trade_in = EQUIPMENT[existing_laser_name]['price'] if existing_laser_name else 0

    #check affordability
    if player.credits >= EQUIPMENT[laser_name]['price'] - trade_in:
        
        if laser_name == "Pulse Laser":
            ship_data.lasers[location_index] = LaserType.PULSE
        elif laser_name == "Beam Laser":
            ship_data.lasers[location_index] = LaserType.BEAM
        elif laser_name == "Military Laser":
            ship_data.lasers[location_index] = LaserType.MILITARY
        elif laser_name == "Mining Laser":
            ship_data.lasers[location_index] = LaserType.MINING

        cost = EQUIPMENT[laser_name]['price'] - trade_in
        player.credits -= cost

        location_map = {'F': "Front", 'B':"Back" , 'L': "Left", 'R': "Right"}
        location_name = location_map.get(location.upper(), None)
        status.add_message(f"{get_text('equipped')} {location_name} {laser_name} {get_text('for')} {cost} {get_text('Cr')}", duration=3, type=0)
    else:
        status.add_message(f"{get_text('not_enough_credits')} {laser_name}", duration=3, type=0)

    return

def process_generic_equipment_addition(equipment_name,cost):
    equipment_attr_map = {
        "Large Cargo Bay": "large_cargo_bay",
        "E.C.M. System": "ECM_System",
        "Fuel Scoops": "fuel_scoops",
        "Escape Capsule": "escape_capsule",
        "Energy Bomb": "energy_bomb",
        "Extra Energy Unit": "extra_energy_unit",
        "Docking Computer": "docking_computer",
        "Galactic Hyperdrive": "galactic_hyperdrive",
    }
    attr = equipment_attr_map.get(equipment_name)
    if attr:
        if not getattr(ship_data, attr):
            setattr(ship_data, attr, True)
            player.credits -= cost
            status.add_message(f"{get_text('equipped')} {equipment_name} {get_text('for')} {cost} {get_text('Cr')}", duration=3, type=0)
        else:
            status.add_message(f"{equipment_name} {get_text('already_equipped')}", duration=3, type=0)

def draw_fuel_circle(center_x, center_y, radius, scale):
    pixel_radius = radius * scale / 0.4
    glColor4f(0, 1, 0, 0.5)
    glLineWidth(3.0)
    num_segments = 60
    import numpy as np
    glBegin(GL_LINE_LOOP)
    for angle in np.linspace(0, 2 * np.pi, num_segments):
        x = center_x + pixel_radius * np.cos(angle)
        y = center_y + pixel_radius * np.sin(angle)
        glVertex2f(x, y)
    glEnd()    

def check_cross_hairs_within_bounds(crosshair_x, crosshair_y, chart_left, chart_top, chart_width, chart_height,position_xy):
    if crosshair_x < chart_left:
        crosshair_x = chart_left
        position_xy = (position_xy[0]+1, position_xy[1])
    elif crosshair_x > chart_left + chart_width:
        crosshair_x = chart_left + chart_width
        position_xy = (position_xy[0]-1, position_xy[1])
    if crosshair_y < chart_top:
        crosshair_y = chart_top
        position_xy = (position_xy[0], position_xy[1]+1)
    elif crosshair_y > chart_top + chart_height:
        crosshair_y = chart_top + chart_height
        position_xy = (position_xy[0], position_xy[1]-1)
    return position_xy


def draw_cross_hairs(x, y,color,size=10,):
    glColor4f(color[0], color[1], color[2], color[3])
    glLineWidth(2)
    # Horizontal line
    glBegin(GL_LINES)
    glVertex2f(x - size, y)
    glVertex2f(x + size, y)
    glEnd()
    # Vertical line
    glBegin(GL_LINES)
    glVertex2f(x, y - size)
    glVertex2f(x, y + size)
    glEnd()    

def draw_dots(x, y, color, size):
    glEnable(GL_POINT_SMOOTH)
    glPointSize(size)
    glColor4f(color[0], color[1], color[2], color[3])
    glBegin(GL_POINTS)
    glVertex2f(x, y)
    glEnd()   