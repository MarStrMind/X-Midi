import mido
import sys
import json
import keyboard
from time import sleep
from xpudp import *

# For knobs and sliders
kn_interrupt = []
kn_value = []
kn_dataref = []
bt_toggle = []

# Delta at which a knob turning motion in one direction is being detected
kn_tr_amount = 1

# Active layer
act_layer = 1

# For sending signals to the target device
# - will be opened at init
midi_out = None

# Global array
json_data = []
dataref_data = []

# Wait for a short amount of time before the next loop iteration
needsleep = True

# The dataref object
dref = None


# Send a midi signal
def send_midi(type, note, data):
	global midi_out
	midi_out.send(mido.Message(type, note=note, velocity=data))


# Attempt to reset lights
def reset_lights():
	for i in range(127):
		send_midi("note_on", i, 0)


# Change layer
def change_active_layer(direction):
    global act_layer
    if direction == "up":
        act_layer = act_layer + 1
    elif direction == "down":
        act_layer = act_layer - 1
        if act_layer < 1:
            act_layer = 1


# Press and release a key with or without modifier
def press_key(key, mod, func="normal"):
    if key == "layer_up" or key == "layer_down":
        if key == "layer_up": change_active_layer("up")
        if key == "layer_down": change_active_layer("down")

    else:
        if func == "normal":
            if mod:
                keyboard.press_and_release(mod+"+"+key)
            else:
                keyboard.press_and_release(key)
        elif func == "press":
            if mod:
                keyboard.press(mod+"+"+key)
            else:
                keyboard.press(key)
        elif func == "release":
            if mod:
                keyboard.release(mod+"+"+key)
            else:
                keyboard.release(key)
        


# Handles a MIDI event.
# Acts depending on what the event is.
def handle_midi_message(message):
    global act_layer
    global json_data
    global dataref_data
    global needsleep
    global dref
    
    for trigger in json_data["triggers"]:
        if trigger["layer"] == act_layer or trigger["layer"] == "all":
            if trigger["type"] == "button":
                handle_button_event(message, trigger)
            elif trigger["type"] == "knob":
                handle_knob_event(message, trigger)
            elif trigger["type"] == "slider":
                handle_slider_event(message, trigger)

def handle_button_event(message, trigger):
    if message.type == "note_on":
        cn = message.channel
        nt = message.note
        if trigger["control"] == nt and trigger["channel"] == cn and (trigger["layer"] == act_layer or trigger["layer"] == "all"):
            if trigger["trigger"] == "toggle":
                for t in range(0, len(bt_toggle)):
                    if bt_toggle[t][0] == message.note and bt_toggle[t][1] == message.channel:
                        if bt_toggle[t][2] == 0:
                            bt_toggle[t][2] = 1
                        else:
                            bt_toggle[t][2] = 0
                        break
            
            k = trigger["key"]
            m = trigger["mod"]
            press_key(k, m)
            
def handle_knob_event(message, trigger):
    global kn_value
    global kn_tr_amount
    global kn_dataref

    if json_data["knob_trigger_amount"]:
        kn_tr_amount = json_data["knob_trigger_amount"]

    if message.type == "control_change":
        c = message.control
        v = message.value
        cn = message.channel

        if trigger["control"] == c and trigger["channel"] == cn:
            knpos = find_knob_position(c, cn)
            handle_knob_initial_value(knpos, v)
            engage_soft_clutch(knpos, v)
            release_interrupt_if_needed(knpos, v)

            if "dataref" in trigger:
                handle_knob_dataref_event(trigger, knpos, v)

            if "events" in trigger:
                handle_knob_events(trigger, knpos, v)

def find_knob_position(c, cn):
    for k in range(len(kn_value) - 1):
        if kn_value[k][0] == c and kn_value[k][1] == cn:
            return k
    return -1

def handle_knob_initial_value(knpos, v):
    if kn_value[knpos][5] == 1:
        kn_value[knpos][5] = 0
        kn_value[knpos][2] = v

def engage_soft_clutch(knpos, v):
    if v == 0 or v == 127:
        kn_value[knpos][3] = 1
        kn_value[knpos][4] = int(v == 127)

def release_interrupt_if_needed(knpos, v):
    if kn_value[knpos][3] == 1:
        if kn_value[knpos][4] == 0 and v >= json_data["interrupt_release"]:
            kn_value[knpos][2] = v
            kn_value[knpos][3] = 0
        elif kn_value[knpos][4] == 1 and v <= 127 - json_data["interrupt_release"]:
            kn_value[knpos][2] = v
            kn_value[knpos][3] = 0

def handle_knob_dataref_event(trigger, knpos, v):
    drefpos = find_dataref_position(trigger["dataref"])
    if kn_value[knpos][3] == 0:
        val = kn_dataref[drefpos][3]
        step_value, max_value, min_value = get_step_max_min_values(trigger["dataref"])
        if v >= (kn_value[knpos][2] + kn_tr_amount):
            val += step_value
        elif v <= (kn_value[knpos][2] - kn_tr_amount):
            val -= step_value
        kn_value[knpos][2] = v
        val = max(min(val, max_value), min_value)
        kn_dataref[drefpos][3] = val
        dref.WriteDataRef(trigger["dataref"], val)

def find_dataref_position(dataref):
    for dr in range(len(kn_dataref)):
        if kn_dataref[dr][2] == dataref:
            return dr
    return -1

def get_step_max_min_values(dataref):
    for d in dataref_data["datarefs"]:
        if d["dataref"] == dataref:
            return d["step"], d["maximum"], d["minimum"]
    return 0, 0, 0

def handle_knob_events(trigger, knpos, v):
    if kn_value[knpos][3] == 0:
        for event in trigger["events"]:
            l = event["change"]
            k = event["key"]
            m = event["mod"]

            if l == "increase" and v >= (kn_value[knpos][2] + kn_tr_amount):
                needsleep = False
                kn_value[knpos][2] = v
                press_key(k, m)
            elif l == "decrease" and v <= (kn_value[knpos][2] - kn_tr_amount):
                needsleep = False
                kn_value[knpos][2] = v
                press_key(k, m)

def handle_slider_event(message, trigger):
    global sl_value

    if message.type == "control_change":
        v = message.value
        c = message.control
        cn = message.channel

        if trigger["control"] == c and trigger["channel"] == cn:
            for event in trigger["events"]:
                if v == event["value"]:
                    k = event["key"]
                    m = event["mod"]

                    needsleep = False
                    press_key(k, m)


# Display MIDI messages of the device specified
def handle_midi_test(message):
	print(f"{message}")

# Find all knobs and give them an initial value
def find_all_knobs(json_data):
	for t in json_data["triggers"]:
		if t["type"] == "knob" and "events" in t:
			if [t["control"], t["channel"], 0] not in kn_value:
				# Control, Channel, Value, 0/1 - Interrupt on, 0/1 - direction of interrupt, catch initial value = true (1)
				kn_value.append([t["control"], t["channel"], 1, 0, 0, 1])

# Find all entries that want to change datarefs
def find_all_datarefs(json_data):
	for t in json_data["triggers"]:
		if t["type"] == "knob" and "dataref" in t:
			# Control, Channel, Dataref, Value
			kn_dataref.append([t["control"], t["channel"], t["dataref"], 0])

			# I set a value of 0 first. When the script initializes,
			# it reads the values from the datarefs we want and places them
			# in this array as initial value. From there on in we can adjust
			# the values we want. For example heading.

# We want to add all buttons that function as toggles
def find_all_toggles(json_data):
    for t in json_data["triggers"]:
        if t["type"] == "button" and t["trigger"] == "toggle":
            bt_toggle.append( [ t["control"], t["channel"], 0, t["layer"] ] )

# List MIDI devices
if sys.argv[1] == "--list":
	print()
	print("Available MIDI input ports:")
	if len(mido.get_input_names()) > 0:
		for port in mido.get_input_names():
			print("- " + port)
	print()
	print("Available MIDI output ports:")
	if len(mido.get_output_names()) > 0:
		for port in mido.get_output_names():
			print("- " + port)
	print()
	sys.exit()


# Test messages of the specified MIDI device
if sys.argv[1] == "--test":
	midi_out = mido.open_output(sys.argv[3])
	try:
		midi_in = mido.open_input(sys.argv[2])

		while True:
			for message in midi_in.iter_pending():
				handle_midi_test(message)

	except KeyboardInterrupt:
		print("input stopped")

	if midi_in:
		midi_in.close()


# Main call
if len(mido.get_input_names()) > 0 and sys.argv[1] != "--list" and sys.argv[1] != "--test":

    json_profile = sys.argv[1]
    with open(json_profile, "r") as json_f:
        json_data = json.loads(json_f.read())

    dataref_profile = "./dataref.json"
    with open(dataref_profile, "r") as dataref_f:
        dataref_data = json.loads(dataref_f.read())
    
    dref = XPlaneUdp();
    dref.FindIp()
    
    input_port_name = json_data["input"]
    output_port_name = json_data["output"]

    find_all_knobs(json_data)
    find_all_datarefs(json_data)
    find_all_toggles(json_data)

    # Add the datarefs we want
    for d in kn_dataref:
        dref.AddDataRef(d[2])

    # Now read the dataref values
    drefval = dref.GetValues()
    for dr in range(0, len(kn_dataref)):
        kn_dataref[dr][3] = drefval[kn_dataref[dr][2]]

    midi_in = mido.open_input(input_port_name)
    midi_out = mido.open_output(output_port_name)

    def handle_colors(json_data):
        if "colors" in json_data:
            clr = json_data["colors"]
            for b in json_data["triggers"]:
                if b["type"] == "button" and "color" in b:
                    cidx = next((i for i, c in enumerate(clr) if c["color"] == b["color"]), -1)
                    if cidx != -1:
                        if b["trigger"] == "toggle":
                            if [b["control"], b["channel"], 1, act_layer] in bt_toggle:
                                send_midi("note_on", b["colorpad"], clr[cidx]["number"])
                            if [b["control"], b["channel"], 0, act_layer] in bt_toggle:
                                send_midi("note_on", b["colorpad"], 0)
                            if [b["control"], b["channel"], 1, act_layer] not in bt_toggle:
                                send_midi("note_on", b["colorpad"], 0)
                        else:
                            if b["layer"] == act_layer:
                                send_midi("note_on", b["colorpad"], clr[cidx]["number"])
                            else:
                                send_midi("note_on", b["colorpad"], 0)

    # Initial light-up
    handle_colors(json_data)

    try:
        while True:
            for message in midi_in.iter_pending():
                handle_midi_message(message)
                handle_colors(json_data)
            sleep(.05)

    except KeyboardInterrupt:
        reset_lights()
        print("input stopped")

    if midi_in:
        midi_in.close()
