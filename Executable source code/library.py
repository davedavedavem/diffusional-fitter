import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from scipy import stats

"""
reads data from CV data files generated by various potentiostat programs and returns 
pandas dataframe with potential, current, and time columns
"""


def CV_reader(userinput_dict):
    if userinput_dict["data_format"] == "CH Instruments text file":
        with open(userinput_dict["filename"], "r", encoding="utf-8") as file:
            lines = file.readlines()
            counter = 0
            for line in lines:
                if line.count("Scan Rate (V/s) =") == 1:
                    rate_char = line.find("=") + 2
                    scan_rate = float(line[rate_char:])

                if line.count("Sample Interval (V)") == 1:
                    interval_char = line.find("=") + 2
                    V_per_index = float(line[interval_char:])

                # find header line and detect delimiter
                if line.count("Potential/V") == 1:
                    header_lines = counter
                    separator_char = line.find("V") + 1
                    separator = repr(line[separator_char]).strip("'")
                counter += 1

        df = pd.read_csv(
            userinput_dict["filename"], skiprows=header_lines, sep=separator
        )
        df.columns = ["E", "I"]
        time = df.index * V_per_index / scan_rate
        df["Time"] = time
        return df

    if userinput_dict["data_format"] == "Nova ASCII export":
        # use pandas drop and rename to tidy df
        df = pd.read_csv(userinput_dict["filename"])
        # remove subsequent scans in case they're accidently included and tidy df
        df = df[df["Scan"] == 1]
        df = df.drop(
            columns=[
                "WE(1).Potential (V)",
                "Scan",
                "Index",
                "Q+",
                "Q-",
                "Current range",
            ]
        )
        df = df.rename(
            columns={
                "Potential applied (V)": "E",
                "Time (s)": "Time",
                "WE(1).Current (A)": "I",
            }
        )
        # correction for t_0 not == 0
        df["Time"] = df["Time"] - df["Time"][0]
        return df

    if userinput_dict["data_format"] == "PSTrace CSV export":
        # read in data to dataframe
        df = pd.read_csv(userinput_dict["filename"], header=4, encoding="utf-16_le")
        df.columns = ["E", "I"]
        # remove byte order mark and convert data to float
        df = df[df["E"] != "\ufeff"]
        df = df.astype(float)

        # read current header to find current magnitude and convert to A
        with open(userinput_dict["filename"], "r", encoding="utf-16") as file:
            lines = file.readlines()
            scale_char = lines[5].find(",") + 1
            scaler = lines[5][scale_char]
        if scaler == "m":
            df["I"] *= 1e-3
        if scaler == "µ":
            df["I"] *= 1e-6
        if scaler == "n":
            df["I"] *= 1e-9
        if scaler == "p":
            df["I"] *= 1e-12

        # use scanrate from userinput_dict to generate time column
        V_per_index = abs(
            round(
                (df["E"].max() - df["E"].min()) / (df["E"].idxmax() - df["E"].idxmin()),
                3,
            )
        )
        time = df.index * V_per_index / userinput_dict["scan_rate"]
        df["Time"] = time

        return df

    if userinput_dict["data_format"] == "Template CSV file":
        with open(userinput_dict["filename"], "r", encoding="utf-8") as file:
            lines = file.readlines()
            rate_char = lines[0].find(",")
            scan_rate = float(lines[0][rate_char + 1 :])

        # create df using filename and remove NaN rows and columns in case template file was modified
        df = pd.read_csv(
            userinput_dict["filename"], skiprows=1, encoding="utf-8", sep=","
        )
        df = df.dropna(axis=0, how="all")
        df = df.dropna(axis=1, how="all")
        df.columns = ["E", "I"]

        # calculate V_per_index and use scan_rate to calculate time column
        V_per_index = abs(
            round(
                (df["E"].max() - df["E"].min()) / (df["E"].idxmax() - df["E"].idxmin()),
                3,
            )
        )
        time = df.index * V_per_index / scan_rate
        df["Time"] = time
        return df


# creates a CV object with associated summary stats
class CV:
    def __init__(self, userinput_dict):

        df = CV_reader(userinput_dict)
        self.filename = userinput_dict["filename"]
        self.dataframe = df

        # assign variables
        self.i_min_pot = df["E"].idxmin()
        self.i_max_pot = df["E"].idxmax()
        self.max_pot = df["E"][self.i_max_pot]
        self.min_pot = df["E"][self.i_min_pot]
        self.V_per_index = abs(
            round((self.max_pot - self.min_pot) / (self.i_max_pot - self.i_min_pot), 3)
        )

        peak_width = int(
            0.03 / self.V_per_index
        )  # 30 mV peak width used as parameter in find_peaks

        ox_peaks, ox_peak_props = find_peaks(
            np.array(df["I"]), width=peak_width, height=0
        )

        red_peaks, red_peak_props = find_peaks(
            -np.array(df["I"]), width=peak_width, height=0
        )

        # find larger peak for scaling
        if df["I"][ox_peaks[0]] > abs(df["I"][red_peaks[0]]):
            scaling_current = df["I"][ox_peaks[0]]
        else:
            scaling_current = abs(df["I"][red_peaks[0]])

        # current auto-scaling
        if 1 > scaling_current >= 1e-3:
            df["I"] *= 10**3
            report_scale_prefix = scale_prefix = "m"

        elif 1e-3 > scaling_current >= 1e-6:
            df["I"] *= 10**6
            scale_prefix = "\u03BC"
            report_scale_prefix = "u"

        elif 1e-6 > scaling_current >= 1e-9:
            df["I"] *= 10**9
            report_scale_prefix = scale_prefix = "n"

        elif 1e-9 > scaling_current:
            df["I"] *= 10**12
            report_scale_prefix = scale_prefix = "p"

        self.scale_prefix = scale_prefix
        self.report_scale_prefix = report_scale_prefix

        # oxidation
        i_ox_peak_current = ox_peaks[0]
        i_min_pot = df["E"].idxmin()
        ox_peak_current = df["I"].iloc[i_ox_peak_current]
        Ep_ox = df["E"].iloc[i_ox_peak_current]

        # reduction
        i_red_peak_current = red_peaks[0]
        i_max_pot = df["E"].idxmax()
        red_peak_current = df["I"].iloc[i_red_peak_current]
        Ep_red = df["E"].iloc[i_red_peak_current]

        # positions in terms of time
        t_ox_peak_current = df["Time"].iloc[i_ox_peak_current]
        t_red_peak_current = df["Time"].iloc[i_red_peak_current]

        # define ox/red parameters in terms of sequence/time
        if i_ox_peak_current < i_red_peak_current:
            (
                self.i_1st_peak,
                self.i_2nd_peak,
                self.t_1st_peak,
                self.t_2nd_peak,
                self.backpeak_current,
                self.forwardpeak_current,
            ) = (
                i_ox_peak_current,
                i_red_peak_current,
                t_ox_peak_current,
                t_red_peak_current,
                red_peak_current,
                ox_peak_current,
            )
        else:
            (
                self.i_1st_peak,
                self.i_2nd_peak,
                self.t_1st_peak,
                self.t_2nd_peak,
                self.backpeak_current,
                self.forwardpeak_current,
            ) = (
                i_red_peak_current,
                i_ox_peak_current,
                t_red_peak_current,
                t_ox_peak_current,
                ox_peak_current,
                red_peak_current,
            )

        # finds index and time of switching potential
        difference_array = np.ones(len(df["E"]))
        i = 1
        while i < len(df["E"]) - 1:
            difference_array[i] = (df["E"][i + 1]) - (df["E"][i - 1])
            i += 1
        self.i_switch_pot = np.argmin(abs(difference_array))
        self.t_switch_pot = df["Time"][self.i_switch_pot]

        # potential stats
        self.E_half = (Ep_ox + Ep_red) / 2
        self.delta_Ep = abs(Ep_ox - Ep_red)

    def __str__(self):
        return f"CV class created from following file:\n\t{self.filename}"


# performs moving linear fit and returns fit with lowest absolute slope
def linear_base_fit(CV, start, fit_range):

    # select initial range and perform initial linear fit
    x_reg = np.array(CV.dataframe["Time"].iloc[start : start + fit_range])
    y_reg = np.array(CV.dataframe["I"].iloc[start : start + fit_range])
    baseline = stats.linregress(x_reg, y_reg)

    # perform series of linear fits and keep one with lowest absolute slope
    counter = 1
    while start + fit_range + counter < CV.i_1st_peak:
        new_x = np.array(
            CV.dataframe["Time"].iloc[start + counter : start + fit_range + counter]
        )
        new_y = np.array(
            CV.dataframe["I"].iloc[start + counter : start + fit_range + counter]
        )
        new_fit = stats.linregress(new_x, new_y)
        counter += 1
        if abs(new_fit.slope) < abs(baseline.slope):
            baseline = new_fit
            x_reg = new_x
            y_reg = new_y

    return baseline, x_reg, y_reg


# R_squared function used in diffusional fitting
def R_squared(observed_y, predicted_y):
    residuals = observed_y - predicted_y
    residuals_ss = np.sum(residuals**2)  # residual sum of squares
    total_ss = np.sum((observed_y - np.mean(observed_y)) ** 2)  # total sum of squares
    return 1 - (residuals_ss / total_ss)


def diffusional_fit(cv, userinput_dict, fitting_bounds, fitting_func):
    # USER DEFINED FITTING RANGE
    if not userinput_dict["fit_range_check"]:
        # find closest time values to those specified by user
        left_fit_limit = np.abs(
            np.array(cv.dataframe["Time"] - float(userinput_dict["dif_fit_start"]))
        ).argmin()
        right_fit_limit = np.abs(
            np.array(cv.dataframe["Time"] - float(userinput_dict["dif_fit_end"]))
        ).argmin()

        # create arrays for fitting
        x_fit = np.array(cv.dataframe["Time"].iloc[left_fit_limit:right_fit_limit])
        y_fit = np.array(cv.dataframe["I"].iloc[left_fit_limit:right_fit_limit])

        # diffusional fitting fitting
        popt, pcov = curve_fit(fitting_func, x_fit, y_fit, bounds=fitting_bounds)

        # calculate r-squared value
        r_squared = R_squared(y_fit, fitting_func(x_fit, *popt))

        return popt, x_fit, r_squared

    # AUTOMATIC FITTING RANGE DETECTION
    # find 50 mV from Ep to use as left end for fitting
    left_fit_margin = int(0.05 / cv.V_per_index)
    left_fit_limit = cv.i_1st_peak + left_fit_margin
    right_fit_limit = cv.i_switch_pot

    # perform initial fit and calculate R-squared
    x_fit = np.array(cv.dataframe["Time"].iloc[left_fit_limit:right_fit_limit])
    y_fit = np.array(cv.dataframe["I"].iloc[left_fit_limit:right_fit_limit])

    # diffusional fitting
    popt, pcov = curve_fit(fitting_func, x_fit, y_fit, bounds=fitting_bounds)

    # calculate r-squared value
    r_squared = R_squared(y_fit, fitting_func(x_fit, *popt))

    # shrinking algorithm
    counter = 1
    while (cv.i_switch_pot - counter - left_fit_limit) * cv.V_per_index > 0.03:
        new_x = np.array(
            cv.dataframe["Time"].iloc[left_fit_limit : cv.i_switch_pot - counter]
        )
        new_y = np.array(
            cv.dataframe["I"].iloc[left_fit_limit : cv.i_switch_pot - counter]
        )
        new_popt, new_pcov = curve_fit(
            fitting_func, new_x, new_y, bounds=fitting_bounds
        )

        # calculate r-squared value
        new_r_squared = R_squared(new_y, fitting_func(new_x, *popt))

        if new_r_squared > r_squared:
            x_fit = new_x
            y_fit = new_y
            r_squared = new_r_squared
            popt, pcov = new_popt, new_pcov

        if r_squared > 0.999:
            break

        counter += 1

    return popt, x_fit, r_squared


# writes summary txt file after fitting
def summary_writer(
    name, cv, userinput_dict, popt, baseline, peak_dict, x_reg, x_fit, r_squared
):
    if userinput_dict["dif_func"] == "Cottrellian":
        fitted_param_string = (
            f"k = {popt[0]} {cv.report_scale_prefix}C / s^(1/2)\nt' = {popt[1]} s\n"
        )
        fitting_func_string = f"Fitting function: k/sqrt(t-t') + {baseline.slope} + {baseline.intercept}*t\n"

    else:
        fitted_param_string = f"k = {popt[0]} {cv.report_scale_prefix}C / s^(1/2)\nt' = {popt[1]} s\na = {popt[2]} {cv.report_scale_prefix}A\n"
        fitting_func_string = f"Fitting function: a + k/sqrt(t-t') + 0.2732 * a * exp[(-0.9961 * |a|) / sqrt(t-t')] + {baseline.slope} + {baseline.intercept}*t\n"

    with open(f"{userinput_dict['output_dir']}/{name}.txt", "w") as summary:
        summary.write("DIFFUSIONAL FITTER SUMMARY\n")
        summary.write(f"File: {userinput_dict['filename']}\n")
        summary.write(
            f"Delta Ep: {cv.delta_Ep} V, Ip1: {peak_dict['Ip1']} {cv.report_scale_prefix}A, Ip2: {peak_dict['Ip2']} {cv.report_scale_prefix}A, peak ratio: {peak_dict['peak_ratio']}\n\n"
        )

        summary.write("LINEAR FIT (Forward peak baseline)\n")
        if userinput_dict["cap_check"]:
            summary.write("Fitting range selection: automatic\n")
        else:
            summary.write("Fitting range selection: manual\n")
        summary.write(f"Linear fit range: {x_reg[0]} - {x_reg[len(x_reg)-1]} s\n")
        summary.write(f"Fitting function: slope*t + intercept\n")
        summary.write(
            f"slope: {str(baseline.slope)} {cv.report_scale_prefix}A / s\nintercept: {str(baseline.intercept)} {cv.report_scale_prefix}A\nR-squared: {str(baseline.rvalue**2)}\n\n"
        )

        summary.write(f"{userinput_dict['dif_func'].upper()} FIT (Backpeak baseline)\n")
        if userinput_dict["fit_range_check"]:
            summary.write("Fitting range selection: automatic\n")
        else:
            summary.write("Fitting range selection: manual\n")

        summary.write(
            f"{userinput_dict['dif_func']} fit range: {x_fit[0]} - {x_fit[len(x_fit)-1]} s\n"
        )
        summary.write(fitting_func_string)
        summary.write(fitted_param_string)
        summary.write(f"R-squared: {r_squared}\n")
