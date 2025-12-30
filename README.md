# X-Midi

A Python implementation allowing for advanced use of MIDI controllers for the X-Plane flight simulator, and potentially other simulators or tools.

The primary aim of this script is the relatively straight-forward use of practically any MIDI controller in existence, with X-Plane. It is designed in such a way that it would be theoretically possible to have only one controller, and control an entire Boeing or Airbus with it - regardless of the size of the controller.

I have personally successfully flown the Cessna Skyhawk 172 and the Cirrus Vision Jet SF-50 to multiple destinations using this implementation.

In theory, you could also use this script and your MIDI controller to control your Twitch livestream, effectively turning your MIDI controller into an advanced Stream Deck. In more extreme scenarios, you could control your plane AND your stream at the same time. The only limit is your imagination, really.

## Requirements

- One of these: Windows, Linux (or Unix-like), macOS
- Python 3.13+
- Ability to either create pip packages system wide OR
- Ability to create a Python virtual environment and install pip packages in that environment

**Important note:**
On Windows systems, this script may not require administrative priviliges to use the keyboard module and emulate keypresses. On Linux systems, you may need to run the script using the ```sudo``` command.

## Installation

Either
- clone this repository to a folder of your choice
- download the zip of this repo, and extract it to a folder of your choice

Then, you will need to install the required Python modules. I highly recommend creating a virtual environment within the folder where this script is located, to keep modules separate from other projects or installations you may have.

Navigate to the folder where this script is located, and open a terminal of your choice on your OS.

Next, instruct pip to install the needed modules:

```pip install -f ./requirements.txt```

This will everything you need.

## Usage

In essence, you run the script and tell the script which configration you want to use. In this repo, I have included my working example for the Samson Conspiracy controller.

- Navigate to the folder where this script is located
- Run Python with the script, plus the configuration file you want to use:

```python ./X-Midi.py ./NameOfYourConfigFile.json```

**Note**
I am not using any sliders on my controller right now, but they also work. See below on how to create your own configuration which can include sliders.

## Configuration files

This repo contains a working example for the Samson Conspiracy controller, but chances are you have a different one. Earlier development of this script was done with an Akai APC Mini.

The configurations are JSON files. They basically describe which device you want to use, and what is supposed to happen when certain conditions are met. For example a certain button is pressed.

In addition, it is possible to have an unlimited number of layers, thereby allowing to use the same control for different actions. With this mechanic you can have, say, autopilot controls on layer 1, and overhead panel controls on layer 2 - all on the same controller.

Either create a new blank JSON file or copy my example and rename it to whatever you want.

- You will first need to find the Input and Output names - see the below section on how to do that.
- You may also want to test your MIDI controller to see which values are on which control - see the section below on how to do that.

Put in your Input and Output names first:

```
{
    "input": "Input Name 0",
    "output": "Output Name 1"
}
```

Next, define your knob trigger amount - the delta amount at which the script detects a decrease or increase of a value:

```
{
    "input": "Input Name 0",
    "output": "Output Name 1",
    "knob_trigger_amount": 1
}
```

Next, put in your triggers section - the area that defines what is happening at certain events... basically the Big Mac, the heart of this implementation:

```
{
    "input": "Input Name 0",
    "output": "Output Name 1",
    "knob_trigger_amount": 1,
    "triggers":
    [
    ]
}
```

Within the "triggers" area, we can begin to define what we want to happen. Below is a simple example for a

- Knob
- Button
- Slider

These are, to my knowledge, covering all available controls on a MIDI controller. From there on in, you should be able to customize and extend your own configuration.

```
{
    "input": "Input Name 0",
    "output": "Output Name 1",
    "knob_trigger_amount": 1,
    "slider_trigger_amount": 1,
    "triggers":
    [
        {
            "type": "knob",
            "control": 16,
            "channel": 0,
            "interrupt": 41,
            "layer": 1,
            "events":
            [
                { "change": "increase", "key": "r", "mod": "" },
                { "change": "decrease", "key": "o", "mod": "" }
            ]
        },

        {
            "type": "button",
            "control": 46,
            "channel": 0,
            "key": "f",
            "mod": "shift",
            "layer": 1,
            "trigger": "normal"
        },

        {
            "type": "slider",
            "control": 62,
            "layer": 1,
            "events":
            [
                { "value": 0, "key": "8", "mod": "ctrl" },
                { "value": 127, "key": "8", "mod": "alt" }
            ]
        }
    ]
}
```

**Knobs**

For knobs, there is an important entry: ```interrupt```. You will need to define the button or control you want to press to "interrupt" the reading of this knob.

I have built this as on some controllers, the knobs only go from 0-127 with their signals and do not support other message types. It works like this:

- Knob turned to 127 - but you want to continue turning right - for example your heading bug for your autopilot
- Press your Interrupt button, and rotate the knob left to value 0
- Press your Interrupt button again and turn right

This effectively turns knobs that are limited to 0-127 into knobs that can be turned endlessly. I have used this in my cockpit quite successfully.

You can set which keys are pressed when the value decreases or increases.

**Buttons**

Arguably the easiest to configure - you basically define the control and the channel of the button, and define which keypress should be emitted when this MIDI button is pressed.

```
{
    "type": "button",
    "control": 46,
    "channel": 0,
    "key": "f",
    "mod": "shift",
    "layer": 1,
    "trigger": "normal"
}
```

Triggers are described below.

**Sliders**

Similarly to knobs and buttons, you also need to define what happens when an event for the defined slider occurs. The difference is that you can define what should happen when the slider is at a certain value.

For example, you could emit a keypress for Flaps Up at value 127, Flaps 2 at 60, and Flaps Full at 0. How you manage that, is entirely up to you.

```
{
    "type": "slider",
    "control": 62,
    "channel": 0,
    "layer": 1,
    "events":
    [
        { "value": 0, "key": "8", "mod": "ctrl" },
        { "value": 60, "key": "8", "mod": "shift" },
        { "value": 127, "key": "8", "mod": "alt" }
    ]
}
```

**Modifiers**

The "mod" entry.

Simple: "ctrl", "shift", or "alt".

**Layers**

Define on which layer this action lies.

**Moving between layers**

Instead of a key to press, you declare the special directive ```layer_up``` or ```layer_down``` as the key to be pressed, and that will switch between the layers for you. Modifier keys and layer values are ignored.

For example:

```
{
    "control": 41,
    "channel": 0,
    "type": "button",
    "key": "layer_up",
    "mod": "",
    "layer": 1,
    "trigger": "normal"
},
{
    "control": 42,
    "channel": 0,
    "type": "button",
    "key": "layer_down",
    "mod": "",
    "layer": 1,
    "trigger": "normal"
}
```

**Trigger options**

Some controllers come with pads that can be configured as toggles - meaning when pressed they send a "note-on" message, and when pressed again they send a "note-off" message. On the Samson Conspiracy, I configured some pads as toggles so that the buttons light up when pressed, and turn off when pressed again.

In these situations you can put in the "toggle" directive as trigger mode. The button will then emit a keypress once at the note-on event, and again at the note-off event.

If the MIDI button/pad behaves normally or you do not need this to be monitored, you can use the "normal" directive. The example JSON in this repo for the Conspiracy features both a normal and toggle mode.

**Actions for a control on different layers**

As previously discussed, you can have the same control act differently, depending on the active layer. For example, if you want the same button to emit one shortcut on layer 1, and another on layer 2, the implementation is simple:

```
{
    "type": "button",
    "control": 46,
    "channel": 0,
    "key": "f",
    "mod": "shift",
    "layer": 1,
    "trigger": "normal"
},
{
    "type": "button",
    "control": 46,
    "channel": 0,
    "key": "f",
    "mod": "ctrl",
    "layer": 2,
    "trigger": "normal"
}
```

Notice that for layer 2, Ctrl+F instead of Shift-F will be emitted.


## Finding the device input and output names

In order to populate your JSON file correctly, you will need to know the Input and Output names. I have a function for that, which lists your devices.

- Connect your MIDI controller
- Navigate to the folder of this script
- Run:

```python ./X-Midi.py --list```

You will now see a list of your connected devices and their corresponding Input and Output names.

## Testing your MIDI device

You may want to test if your MIDI device sends signals at all. I did have instances where the device was connected and powered on, but the script did not react as the device did not receieve any signals. In this situation, unplugging and re-plugging the controller did help.

- (Re-) connect your MIDI controller
- Navigate to the folder of this script
- Run:

```python ./X-Midi.py --test "Input Name" "Output Name"```

See the previous section on how to acquire the Input and Output names. The script now waits. As soon as you do something on and/or with your controller - for example turning a knob or pressing a button - you should see what the script has intercepted: the message type and what exactly happened.

You need to use this information to create your own configuration file - I recommend noting the single controls, notes and channels somewhere, so that you can efficiently proceed with your configuration.