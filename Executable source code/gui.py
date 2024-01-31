from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QFormLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QMessageBox,
    QFileDialog,
    QRadioButton,
    QHBoxLayout,
    QComboBox,
    QInputDialog,
)
from PyQt5.QtGui import QIcon
import fitter
import sys, os


def main():
    # finds temp file for icon path
    if getattr(sys, "frozen", False):
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    app = QApplication([])
    app.setStyle("Fusion")
    window = QWidget()
    window.setWindowTitle("Diffusional Fitter")
    window.setWindowIcon(QIcon(application_path + "/icon.ico"))
    window.resize(300, 200)
    layout = QFormLayout()

    # Selection for input file format
    layout.addRow(QLabel("Select data format"))
    format_selector = QComboBox()
    format_selector.addItems(
        [
            "Template CSV file",
            "CH Instruments text file",
            "Nova ASCII export",
            "PSTrace CSV export",
        ]
    )
    layout.addRow(format_selector)
    layout.addRow(QLabel(""))  # empty row for spacing

    # Selections for input file and output directory
    data_button = QPushButton("Select CV file")
    output_button = QPushButton("Select output folder")
    l1 = QLabel("Data:")
    l2 = QLabel("Output:")
    layout.addRow(data_button)
    layout.addRow(l1)
    layout.addRow(output_button)
    layout.addRow(l2)
    layout.addRow(QLabel(""))  # empty row for spacing

    # Diffusion function selection
    hbox_dif_selection = QHBoxLayout()
    Cottrell_button = QRadioButton("Cottrellian")
    Cottrell_button.setChecked(True)
    SS_button = QRadioButton("Shoup-Szabo")
    hbox_dif_selection.addWidget(Cottrell_button)
    hbox_dif_selection.addWidget(SS_button)
    layout.addRow(hbox_dif_selection)
    layout.addRow(QLabel(""))  # empty row for spacing

    # capacitance correction
    cap_checkbox = QCheckBox()
    cap_checkbox.setText("Automatic capacitance fit range")
    cap_checkbox.setChecked(True)
    linear_fit_start_input = QLineEdit()
    linear_fit_start_input.setDisabled(True)
    linear_fit_end_input = QLineEdit()
    linear_fit_end_input.setDisabled(True)
    layout.addRow(cap_checkbox)
    layout.addRow("Linear fit start (s)", linear_fit_start_input)
    layout.addRow("Linear fit end (s)", linear_fit_end_input)
    layout.addRow(QLabel(""))  # empty row for spacing

    # options for manual Cottrell fit range selection
    fit_range_box = QCheckBox()
    fit_range_box.setText("Automatic diffusional fit range")
    fit_range_box.setChecked(True)
    left_fit_range_input = QLineEdit()
    left_fit_range_input.setDisabled(True)
    right_fit_range_input = QLineEdit()
    right_fit_range_input.setDisabled(True)

    layout.addRow(fit_range_box)
    layout.addRow("Diffusional fit start (s)", left_fit_range_input)
    layout.addRow("Diffusional fit end (s)", right_fit_range_input)
    layout.addRow(QLabel(""))  # empty row for spacing

    # text input for output file names
    name_input = QLineEdit()
    layout.addRow("Optional: name for plot and summary", name_input)

    # run/about buttons
    hbox_run_about_buttons = QHBoxLayout()
    run_button = QPushButton("Run")
    about_button = QPushButton("About")
    hbox_run_about_buttons.addWidget(run_button)
    hbox_run_about_buttons.addWidget(about_button)
    layout.addRow(hbox_run_about_buttons)

    def data_button_clicked():
        filename_tup = QFileDialog.getOpenFileName()
        filename = filename_tup[0]  # define filename from tuple
        l1.setText(f"Data: {filename}")

    def output_button_clicked():
        l2.setText(f"Output: {QFileDialog.getExistingDirectory()}")

    def about_button_clicked():
        alert = QMessageBox()
        alert.setWindowTitle("About")
        alert.setWindowIcon(QIcon(application_path + "/icon.ico"))
        alert.setTextFormat(1) # sets text format to rich
        alert.setText(
            "Version: 1.0.1 revised on 31/01/2024<br/>"+
            "Diffusional Fitter was created by David S. Macedo and Conor F. Hogan.<br/><br/>"+
            "Source code and additional documentation can be found at <a href='www.github.com/davedavedavem/diffusional-fitter'>www.github.com/davedavedavem/diffusional-fitter</a><br/><br/>"+
            "More information about the fitting process can be found <a href='https://doi.org/10.1021/acs.analchem.3c04181'>here</a> in our paper:<br/>"+
            "<b>More Accurate Measurement of Return Peak Current in Cyclic Voltammetry Using Diffusional Baseline Fitting</b><br/>"+
            "David S. Macedo, Theo Rodopoulos, Mikko Vepsäläinen, Samridhi Bajaj, and Conor F. Hogan<br/>"+
            "<i>Analytical Chemistry</i> <b>2024</b> <i>96</i> (4), 1530-1537<br/>"+
            "DOI: 10.1021/acs.analchem.3c04181"
        )
        alert.exec_()
        return

    def run_button_clicked():
        # preparation of arguments and error checking
        data_format = format_selector.currentText()
        source = l1.text().replace("Data: ", "")
        output = l2.text().replace("Output: ", "")
        name = name_input.text()
        cap_check = cap_checkbox.isChecked()
        lin_fit_start = linear_fit_start_input.text()
        lin_fit_end = linear_fit_end_input.text()
        fit_range_check = fit_range_box.isChecked()
        dif_fit_start = left_fit_range_input.text()
        dif_fit_end = right_fit_range_input.text()
        if Cottrell_button.isChecked():
            dif_func = "Cottrellian"
        else:
            dif_func = "Shoup-Szabo"

        # dict to be passed to fitter func
        userinput_dict = {
            "data_format": data_format,
            "filename": source,
            "output_dir": output,
            "name": name,
            "cap_check": cap_check,
            "lin_fit_start": lin_fit_start,
            "lin_fit_end": lin_fit_end,
            "fit_range_check": fit_range_check,
            "dif_fit_start": dif_fit_start,
            "dif_fit_end": dif_fit_end,
            "dif_func": dif_func,
        }

        # ask for scan rate in case of PS Trace data
        if data_format == "PSTrace CSV export":
            try:
                scan_rate, alert = QInputDialog.getText(
                    QWidget(), "Input text", "Please input scan rate (V/s):"
                )
                userinput_dict.update({"scan_rate": float(scan_rate)})
            except:
                alert = QMessageBox()
                alert.setWindowTitle("Error")
                alert.setText(
                    "Scan rate input required for data from PSTrace CSV export"
                )
                alert.exec_()
                return

        # error management for diffusional fit range
        if not fit_range_check:
            try:
                dif_fit_start = float(dif_fit_start)
                dif_fit_end = float(dif_fit_end)
            except ValueError:
                alert = QMessageBox()
                alert.setWindowTitle("Error")
                alert.setText("Check diffusional fit range")
                alert.exec_()
                return
            if dif_fit_end < dif_fit_start or dif_fit_end < 0 or dif_fit_start < 0:
                alert = QMessageBox()
                alert.setWindowTitle("Error")
                alert.setText("Check diffusional fit range")
                alert.exec_()
                return

        # error management for capacitance input and variable conversion to float
        if not cap_check:
            try:
                lin_fit_start = float(lin_fit_start)
                lin_fit_end = float(lin_fit_end)
            except ValueError:
                alert = QMessageBox()
                alert.setWindowTitle("Error")
                alert.setText("Check linear fit range")
                alert.exec_()
                return
            if lin_fit_end < lin_fit_start or lin_fit_end < 0 or lin_fit_start < 0:
                alert = QMessageBox()
                alert.setWindowTitle("Error")
                alert.setText("Check linear fit range")
                alert.exec_()
                return

        # error check for empty data/output fields
        if l1.text() == "Data:" or l2.text() == "Output:":
            alert = QMessageBox()
            alert.setWindowTitle("Error")
            alert.setText("Please select data and output folders")
            alert.exec_()
            return

        # run fitter script
        try:
            fitter.fitter(userinput_dict)
        except:
            alert = QMessageBox()
            alert.setWindowTitle("Error")
            alert.setText("Something went wrong.")
            alert.exec_()
            return

        # alert message on success
        alert = QMessageBox()
        alert.setWindowTitle("Success")
        alert.setText("Program ran without errors")
        alert.exec_()

    def checkbox_logic():
        # linear capacitance fit
        if cap_checkbox.isChecked():
            linear_fit_start_input.setDisabled(True)
            linear_fit_end_input.setDisabled(True)
        else:
            linear_fit_start_input.setDisabled(False)
            linear_fit_end_input.setDisabled(False)
        # Diffusional fit range
        if fit_range_box.isChecked():
            left_fit_range_input.setDisabled(True)
            right_fit_range_input.setDisabled(True)
        else:
            left_fit_range_input.setDisabled(False)
            right_fit_range_input.setDisabled(False)

    data_button.clicked.connect(data_button_clicked)
    output_button.clicked.connect(output_button_clicked)
    cap_checkbox.stateChanged.connect(checkbox_logic)
    fit_range_box.stateChanged.connect(checkbox_logic)
    about_button.clicked.connect(about_button_clicked)
    run_button.clicked.connect(run_button_clicked)
    window.setLayout(layout)
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
