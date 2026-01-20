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
	n = note
	s = data
	midi_out.send(mido.Message(type, note=n, velocity=s))


# Attempt to reset lights
def reset_lights(mididev):
	for i in range(127):
		send_midi(mididev, "note_on", i, 0)


# Change layer
def change_active_layer(direction):
	global act_layer
	if direction == "up":
		if act_layer >= 1:
			act_layer = act_layer + 1
	if direction == "down":
		if act_layer >= 2:
			act_layer = act_layer - 1
			if act_layer == 0:
				act_layer = 1


# Press and release a key with or without modifier
def press_key(key, mod, func="normal"):
	if func == "normal":
		if mod != "":
			keyboard.press(mod+"+"+key)
			sleep(.05)
			keyboard.release(mod+"+"+key)
		else:
			keyboard.press(key)
			sleep(.05)
			keyboard.release(key)
	if func == "press":
		if mod != "":
			keyboard.press(mod+"+"+key)
		else:
			keyboard.press(key)
	if func == "release":
		if mod != "":
			keyboard.release(mod+"+"+key)
		else:
			keyboard.release(key)
	if key == "layer_up":
		change_active_layer("up")
	if key == "layer_down":
		change_active_layer("down")


# Handles a MIDI event.
# Acts depending on what the event is.
def handle_midi_message(message):
	global act_layer
	global json_data
	global dataref_data
	global needsleep
	global dref
	
	for i in range(len(json_data["triggers"])):
		
		# Only react on those with the current active layer
		if json_data["triggers"][i]["layer"] == act_layer:

			# Button
			if json_data["triggers"][i]["type"] == "button":
				cn = message.channel
				if message.type == "note_on":
					if message.note == json_data["triggers"][i]["control"] and json_data["triggers"][i]["channel"] == cn:
						if json_data["triggers"][i]["key"] == "layerup":
							change_active_layer("up")
						if json_data["triggers"][i]["key"] == "layerdown":
							change_active_layer("down")
						if json_data["triggers"][i]["key"] != "RESET" and json_data["triggers"][i]["key"] != "layerup" and json_data["triggers"][i]["key"] != "layerdown":
							k = json_data["triggers"][i]["key"]
							m = json_data["triggers"][i]["mod"]
							needsleep = False
							press_key(k, m)
				if message.type == "note_off" and message.note == json_data["triggers"][i]["control"] and json_data["triggers"][i]["channel"] == cn and json_data["triggers"][i]["trigger"] == "toggle":
						k = json_data["triggers"][i]["key"]
						m = json_data["triggers"][i]["mod"]
						needsleep = False
						press_key(k, m)

			# A knob has been turned
			if json_data["triggers"][i]["type"] == "knob":
				global kn_value
				global kn_tr_amount
				global kn_dataref

				# Trigger only at delta of this number, if present
				if json_data["knob_trigger_amount"]:
					kn_tr_amount = json_data["knob_trigger_amount"]

				if message.type == "control_change":

					c = message.control
					v = message.value
					cn = message.channel

					if json_data["triggers"][i]["control"] == c and json_data["triggers"][i]["channel"] == cn:

						knpos = -1
						for k in range(0, len(kn_value)-1):
							if kn_value[k][0] == c and kn_value[k][1] == cn:
								knpos = k
								break

						# Note initial value instead of the default value in array
						# then exit loop
						if kn_value[knpos][5] == 1:
							kn_value[knpos][5] = 0
							kn_value[knpos][2] = v
							break

						# Engage soft clutch as needed
						if v == 0:
							kn_value[knpos][3] = 1
							kn_value[knpos][4] = 0
						if v == 127:
							kn_value[knpos][3] = 1
							kn_value[knpos][4] = 1

						# Determine if we need to release the interrupt	
						if kn_value[knpos][3] == 1:
							# Interrupt for left direction, knob needs to be turned right
							# beyond the provided release value
							if kn_value[knpos][4] == 0:
								if v >= 0 + json_data["interrupt_release"]:
									kn_value[knpos][2] = v
									kn_value[knpos][3] = 0
							# Interrupt for right direction, knob needs to be turned left
							# beyond the provided release value
							if kn_value[knpos][4] == 1:
								if v <= 127 - json_data["interrupt_release"]:
									kn_value[knpos][2] = v
									kn_value[knpos][3] = 0

						if "dataref" in json_data["triggers"][i]:

							# First we find the value by which we increase and decrease
							step_value = 0
							max_value = 0
							min_value = 0
							for d in dataref_data["datarefs"]:
								if d["dataref"] == json_data["triggers"][i]["dataref"]:
									step_value = d["step"]
									max_value = d["maximum"]
									min_value = d["minimum"]

							drefpos = -1
							for dr in range(0, len(kn_dataref)):
								if kn_dataref[dr][2] == json_data["triggers"][i]["dataref"]:
									drefpos = dr
									break

							# Only act if interrupt is not active
							if kn_value[knpos][3] == 0:
								val = kn_dataref[drefpos][3]
								if v >= (kn_value[knpos][2] + kn_tr_amount):
									val = kn_dataref[drefpos][3] + step_value

								if v <= (kn_value[knpos][2] - kn_tr_amount):
									val = kn_dataref[drefpos][3] - step_value
								
								kn_value[knpos][2] = v
								if val > max_value:
									val = min_value
								if val < min_value:
									val = max_value
								kn_dataref[drefpos][3] = val
								dref.WriteDataRef(json_data["triggers"][i]["dataref"], val)


						# Non-dataref based, some key should be pressed
						if "events" in json_data["triggers"][i]:
							# Only act if interrupt is not active
							if kn_value[knpos][3] == 0:
								for j in range(len(json_data["triggers"][i]["events"])):
									l = json_data["triggers"][i]["events"][j]["change"]
									k = json_data["triggers"][i]["events"][j]["key"]
									m = json_data["triggers"][i]["events"][j]["mod"]

									if l == "increase":
										if v >= (kn_value[knpos][2] + kn_tr_amount):
											needsleep = False
											kn_value[knpos][2] = v
											press_key(k, m)
											#for p in range(kn_value[knpos][2], kn_value[knpos][2] + kn_tr_amount):
											#	needsleep = False
											#	press_key(k, m)
											
									if l == "decrease":
										if v <= (kn_value[knpos][2] - kn_tr_amount):
											needsleep = False
											kn_value[knpos][2] = v
											press_key(k, m)
											#for p in reversed(range(kn_value[knpos][2] - kn_tr_amount, kn_value[knpos][2])):
											#	needsleep = False
											#	press_key(k, m)

			# Slider went up or down
			if json_data["triggers"][i]["type"] == "slider":
				global sl_value

				if message.type == "control_change":

					v = message.value
					c = message.control
					cn = message.channel

					if json_data["triggers"][i]["control"] == c and json_data["triggers"][i]["channel"] == cn:
						
						for j in range(len(json_data["triggers"][i]["events"])):
							if v == json_data["triggers"][i]["events"][j]["value"]:
								k = json_data["triggers"][i]["events"][j]["key"]
								m = json_data["triggers"][i]["events"][j]["mod"]

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

# List MIDI devices
if sys.argv[1] == "--list":
	print()
	print ("Available MIDI input ports:")
	if len(mido.get_input_names()) > 0:
		for port in mido.get_input_names():
			print("- " + port)
	print()
	print ("Available MIDI output ports:")
	if len(mido.get_output_names()) > 0:
		for port in mido.get_output_names():
			print("- " + port)
	print()
	exit


# Test messages of the specified MIDI device
if sys.argv[1] == "--test":
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
	json_f = open(json_profile, "r")
	json_data = json.loads(json_f.read())

	dataref_profile = "./dataref.json"
	dataref_f = open(dataref_profile, "r")
	dataref_data = json.loads(dataref_f.read())
	
	dref = XPlaneUdp();
	dref.FindIp()
	
	input_port_name = json_data["input"]
	output_port_name = json_data["output"]

	find_all_knobs(json_data)
	find_all_datarefs(json_data)

	# Add the datarefs we want
	for d in kn_dataref:
		dref.AddDataRef(d[2])

	# Now read the dataref values
	drefval = dref.GetValues()
	for dr in range(0, len(kn_dataref)):
		kn_dataref[dr][3] = drefval[kn_dataref[dr][2]]

	if len(sys.argv) == 4:
		midi_out = mido.open_output(output_port_name)

		for i in range(0, 127):
			midi_out.send(mido.Message("note_on", note=i, velocity=0))
			sleep(0.01)

		# Perform init calls
		for i in range(len(json_data["init"])):
			n = json_data["init"][i]["note"]
			s = json_data["init"][i]["signal"]
			midi_out.send(mido.Message("note_on", note=n, velocity=s))
			sleep(0.02)
		midi_out.close()

	try:
		midi_in = mido.open_input(input_port_name)
		midi_out = mido.open_output(output_port_name)

		while True:
			for message in midi_in.iter_pending():
				handle_midi_message(message)
			if needsleep == True:
				sleep(.05)

	except KeyboardInterrupt:
		print("input stopped")

	if midi_in:
		midi_in.close()
