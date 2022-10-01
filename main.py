# Example code for real time plot of Elmor Labs KTH (K-type Thermometer) through USB serial interface
# Real time plotting inspired by https://towardsdatascience.com/plotting-live-data-with-matplotlib-d871fac7500b
# Written by bjorntas

import serial
import serial.tools.list_ports
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.dates as mdates

# settings

kth_settings = {
    'port':'COM9',
    'baudrate':9600,
    'bytesize':8,
    'stopbits':1,
    'timeout':1
}

list_all_windows_ports = True
save_to_csv = True
max_length = 500


def check_connection():

    with serial.Serial(**kth_settings) as ser:

        # b'\x00'   welcome message
        # b'\x01'   device ID
        # b'\x02'   unique ID
        # b'\x03'   firmware version

        # check welcome message
        ser.write(b'\x00')
        ser.flush()
        read_bytes = ser.read(100)
        print(read_bytes)
        #print(b'ElmorLabs KTH-USB')
        #assert read_bytes == b'ElmorLabs KTH-USB'

        ser.write(b'\x01')
        ser.flush()
        read_bytes = ser.read(100)
        print('Device ID: ', read_bytes)
        assert read_bytes == b'\x0d\xee'

        ser.write(b'\x02')
        ser.flush()
        read_bytes = ser.read(100)
        print('Unique ID: ', read_bytes)

        ser.write(b'\x03')
        ser.flush()
        read_bytes = ser.read(100)
        print('Firmware version: ', read_bytes)


def get_new_sensor_values(save_to_csv):

    # b'\x10'   read TC1
    # b'\x11'   read TC2
    # b'\x12'   read VDD
    # b'\x14'   read TH1
    # b'\x15'   read TH2

    df = pd.DataFrame()

    communication_specs = {
        'TC1':[b'\x10', 2, 0.1, 'T', True],
        'TC2':[b'\x11', 2, 0.1, 'T', True],
        'VDD':[b'\x12', 4, 1, 'uV', True],
        'TH1':[b'\x14', 2, 1, 'ADC value', False],
        'TH2':[b'\x15', 2, 1, 'ADC value', False]
    }

    with serial.Serial(**kth_settings) as ser:

        for name, value in communication_specs.items():

            # unpack values
            command, nr_of_bytes, multiplier, unit, signed = value

            timestamp = pd.Timestamp(datetime.today())

            # communicate with KTH thermometer
            ser.write(command)
            ser.flush()
            read_bytes = ser.read(nr_of_bytes)

            # convert byte to int
            result = int.from_bytes(read_bytes[0:nr_of_bytes], byteorder='little', signed=signed) * multiplier

            # add new row to dataframe
            row = pd.DataFrame([[timestamp, name, unit, result]], columns = ['timestamp', 'id', 'unit', 'value'])
            df = pd.concat([df, row], ignore_index=True)

    if save_to_csv:
        df.to_csv('temperature_measurements.csv', mode='a', header=False, index=False)

    return df


def animation_update(i, *fargs):

    # unpack dataframe from input tuple
    df = fargs[0]

    # update data
    df_new_data = get_new_sensor_values(save_to_csv)

    # append new data to old data
    for _, row in df_new_data.iterrows():
        df.loc[df.index.max()+1] = row # pd.concat() does not work

    # remove old data if dataframe is larger than max_length
    if df.shape[0] > max_length:
        for _ in range(len(df_new_data)):
            df.drop(df.index.min(), inplace=True)

    # pivot dataframe
    df_plot = df[df.unit == 'T'].pivot(columns=['id', 'unit'], index='timestamp')

    df_plot.columns = [col[1] for col in df_plot.columns]
           
    # clear axis
    ax.cla()

    # plot temperature scatter
    for col in df_plot.columns:

        df_temp_plot = df_plot[[col]].dropna()
        #ax.scatter(x=df_plot.index, y=df_plot[col], label=col)
        ax.plot(df_temp_plot.index, df_temp_plot[col], label=col)

    ax.legend(loc='center right')

    # set titles
    ax.set_title('Temperature', fontsize=9, color='k')

    # set ylabels
    ax.set_ylabel('Temperate [Celsius]', fontsize=9, color='k')

    # remove spines and ticks
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['bottom'].set_visible(False)


if __name__ == '__main__':

    if list_all_windows_ports:
        ports = list(serial.tools.list_ports.comports())
        print('\nUSB PORTS: ')
        for p in ports:
            print(p)
        print()

    check_connection()

    df = get_new_sensor_values(save_to_csv=False)

    if save_to_csv:
        df.to_csv('temperature_measurements.csv', index=False)

    plt.style.use('ggplot')

    # define and adjust figure
    fig, (ax) = plt.subplots(1, 1, figsize=(8, 7), facecolor='#707576')

    fig.suptitle('Elmor Labs KTH-USB', fontsize=14)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    ax.xaxis.label.set_visible(False)

    # animate
    ani = FuncAnimation(fig, animation_update, fargs=(df,), interval=0)
    fig.tight_layout()
    fig.subplots_adjust(left=0.09)
    plt.show()
