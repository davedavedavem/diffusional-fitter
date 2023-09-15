import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import os
from library import CV, linear_base_fit, summary_writer, diffusional_fit


def fitter(userinput_dict):
    # checks for Cottrellian or Shoup-Szabo option, defines piecewise fitting functions
    if userinput_dict["dif_func"] == "Cottrellian":

        def fitting_func(t, k, t_prime):
            args = (k, t_prime)

            def Cot1(t, k, t_prime):
                return (
                    k / np.sqrt(t - t_prime)
                    + baseline.intercept
                    + baseline.slope * (t)
                )

            def Cot2(t, k, t_prime):
                return (
                    k / np.sqrt(t - t_prime)
                    - baseline.slope * (t - cv.t_switch_pot)
                    - baseline.intercept
                )

            return np.piecewise(
                t, [t <= cv.t_switch_pot, t > cv.t_switch_pot], [Cot1, Cot2], *args
            )

    else:
        def Shoup_Szabo(t, k, t_prime, a):
            return a + k / np.sqrt(t - t_prime) + 0.2732*a*np.exp(-0.9961*abs(a)/np.sqrt(t - t_prime))

        def fitting_func(t, k, t_prime, a):
            args = (k, t_prime, a)

            def SS1(t, k, t_prime, a):

                return (
                    Shoup_Szabo(t, k, t_prime, a)
                    + baseline.intercept
                    + baseline.slope * t
                )

            def SS2(t, k, t_prime, a):

                return (
                    Shoup_Szabo(t, k, t_prime, a)
                    - baseline.slope * (t - cv.t_switch_pot)
                    - baseline.intercept
                )

            return np.piecewise(
                t, [t <= cv.t_switch_pot, t > cv.t_switch_pot], [SS1, SS2], *args
            )

    # create CV object from selected filename
    cv = CV(userinput_dict)

    # set bounds for diffusional fitting function
    if userinput_dict["dif_func"] == "Cottrellian":
        fitting_bounds = ((-np.inf, 0), (np.inf, cv.t_1st_peak))

    else:
        fitting_bounds = ((-np.inf, 0, -np.inf), (np.inf, cv.t_1st_peak, np.inf))

    # check for automatic or user-defined linear fit for first peak and capacitance correction
    if userinput_dict["cap_check"]:
        # intial fit
        baseline, x_reg, y_reg = linear_base_fit(cv, 1, int(0.04 / cv.V_per_index))

    else:
        # find nearest values to user defined range
        left_fit_limit = np.abs(
            np.array(cv.dataframe["Time"] - float(userinput_dict["lin_fit_start"]))
        ).argmin()
        right_fit_limit = np.abs(
            np.array(cv.dataframe["Time"] - float(userinput_dict["lin_fit_end"]))
        ).argmin()
        # use nearest values in linear fit
        x_reg = np.array(cv.dataframe["Time"].iloc[left_fit_limit:right_fit_limit])
        y_reg = np.array(cv.dataframe["I"].iloc[left_fit_limit:right_fit_limit])
        baseline = stats.linregress(x_reg, y_reg)

    # perform diffusional fitting
    popt, x_fit, r_squared = diffusional_fit(
        cv, userinput_dict, fitting_bounds, fitting_func
    )

    # PLOTTING
    # arrays for peak lines in plots
    x_base = np.array(cv.dataframe["Time"][0 : cv.i_1st_peak])
    x_peak = np.array([cv.t_1st_peak, cv.t_1st_peak])
    y_peak = np.array(
        [cv.t_1st_peak * baseline.slope + baseline.intercept, cv.forwardpeak_current]
    )
    x_peak2 = np.array([cv.t_2nd_peak, cv.t_2nd_peak])
    y_peak2 = np.array([fitting_func(cv.t_2nd_peak, *popt), cv.backpeak_current])

    # plot data
    x = np.array(cv.dataframe["Time"])
    y = np.array(cv.dataframe["I"])

    # formatting
    plt.rcParams.update({"font.sans-serif": "Arial"})
    plt.figure(dpi=300)
    plt.title(userinput_dict["name"])
    max_current = cv.dataframe["I"].max()
    min_current = cv.dataframe["I"].min()
    y_scaling = max_current - min_current
    x_scaling = cv.dataframe["Time"].iloc[-1]
    plt.ylim(min_current - 0.1 * y_scaling, max_current + 0.1 * y_scaling)
    plt.ylabel(f"I ({cv.scale_prefix}A)")
    plt.xlabel(f"Time (s)")
    plt.plot(x, y)

    # 1st peak and baseline
    Ip1 = cv.forwardpeak_current - (cv.t_1st_peak * baseline.slope + baseline.intercept)
    plt.plot(x_peak, y_peak, linewidth=2, color="black", ls="dotted")
    plt.plot(
        x_base,
        x_base * baseline.slope + baseline.intercept,
        linewidth=2,
        color="black",
        ls="dotted",
    )
    plt.plot(
        x_reg, x_reg * baseline.slope + baseline.intercept, linewidth=2, color="black"
    )  # linear fit region
    plt.text(
        cv.t_1st_peak - 0.2 * x_scaling,
        cv.forwardpeak_current,
        f"{round(Ip1, 1)} {cv.scale_prefix}A",
    )
    plt.text(
        cv.t_1st_peak + 0.05 * x_scaling,
        0,
        f"Linear fit \nR\u00b2: {round(baseline.rvalue**2, 6)}",
    )

    # 2nd peak and baseline
    plt.plot(x_fit, fitting_func(x_fit, *popt), linewidth=2, color="black")
    Ip2 = cv.backpeak_current - fitting_func(cv.t_2nd_peak, *popt)
    y_peak2 = np.array([fitting_func(cv.t_2nd_peak, *popt), cv.backpeak_current])
    plt.text(
        cv.t_2nd_peak,
        -Ip2,
        f"{userinput_dict['dif_func']} Fit \nR\u00b2: {round(r_squared, 6)}",
    )
    plt.text(
        cv.t_2nd_peak + 0.05 * x_scaling,
        cv.backpeak_current,
        f"{round(Ip2, 1)} {cv.scale_prefix}A",
    )  # Ip label

    # extrapolated baseline
    extrap_x = np.array(
        cv.dataframe["Time"].iloc[
            cv.i_1st_peak + int(0.05 / cv.V_per_index) : cv.i_2nd_peak
        ]
    )
    extrap_x = np.linspace(x_fit[0], cv.t_2nd_peak, 100)
    plt.plot(
        extrap_x, fitting_func(extrap_x, *popt), linewidth=2, color="black", ls="dotted"
    )
    plt.plot(x_peak2, y_peak2, linewidth=2, ls="dotted", color="black")

    # peak ratio calculation and creation of dictionary for summary report
    peak_ratio = abs(round(Ip2 / Ip1, 4))
    plt.text(x_scaling * 0.25, cv.backpeak_current, f"Peak ratio: {peak_ratio}")
    peak_dict = {"Ip1": Ip1, "Ip2": Ip2, "peak_ratio": peak_ratio}

    # check for existing files and increment suffix number to prevent overwriting files
    if userinput_dict["name"] == "":
        name = "Plot"
    else:
        name = userinput_dict["name"]
    name_suffix = 2
    og_name = name
    while os.path.exists(f"{userinput_dict['output_dir']}/{name}.txt"):
        name = og_name + f" {name_suffix}"
        name_suffix += 1

    # save plot and summary file
    plt.savefig(f"{userinput_dict['output_dir']}/{name}.png", format="png", dpi=300)
    summary_writer(
        name, cv, userinput_dict, popt, baseline, peak_dict, x_reg, x_fit, r_squared
    )
