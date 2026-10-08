import win32print


class PrintLabel:
    # max bytes per QR version 1..10, byte mode, error level Q
    QR_CAPACITY_Q = [11, 20, 32, 46, 60, 74, 86, 108, 130, 151]

    def __init__(self, printer_name="ZDesigner GC420t (EPL)",
                 label_width_mm=72, label_height_mm=46,
                 dpi_dots_per_mm=8, qr_mag=6, margin=24):
        self.printer_name = printer_name
        self.label_width = label_width_mm * dpi_dots_per_mm    # 576
        self.label_height = label_height_mm * dpi_dots_per_mm  # 368
        self.qr_mag = qr_mag
        self.margin = margin

    @staticmethod
    def zpl_safe(text):
        return str(text).replace("^", " ").replace("~", " ")

    def qr_size(self, data):
        n = len(data.encode("ascii", errors="replace"))
        for version, cap in enumerate(self.QR_CAPACITY_Q, start=1):
            if n <= cap:
                return (17 + 4 * version) * self.qr_mag
        raise ValueError("QR data too long")

    def build_zpl(self, product, ma, barcode, pon, copies=1):
        product = self.zpl_safe(product)
        ma = self.zpl_safe(ma)
        barcode = self.zpl_safe(barcode)
        pon = self.zpl_safe(pon)

        m = self.margin
        block_w = self.label_width - 2 * m
        size = self.qr_size(barcode)
        qx = self.label_width - m - size      # right-aligned QR
        qy = 122

        if qx < m or qy + size > self.label_height:
            raise ValueError(f"QR ({size} dots) does not fit on the label")

        return (
            "^XA\n"
            "^LH0,0\n"
            "^LS0\n"
            f"^PW{self.label_width}\n"
            f"^LL{self.label_height}\n"
            f"^PQ{int(copies)}\n"
            f"^FO{m},45^FB{block_w},1,0,L,0^A0N,32,32^FDPRODUCT: {product}^FS\n"
            f"^FO{m},90^FB{block_w},1,0,L,0^A0N,32,32^FDMA: {ma}^FS\n"
            f"^FO{qx},{qy}^BQN,2,{self.qr_mag}^FDQA,{barcode}^FS\n"
            f"^FO{m},293^FB{block_w},1,0,L,0^A0N,28,28^FDPON: {pon}^FS\n"
            "^XZ\n"
        )

    def print_label(self, product, ma, barcode, pon, copies=1):
        zpl = self.build_zpl(product, ma, barcode, pon, copies)

        printer = win32print.OpenPrinter(self.printer_name)
        try:
            win32print.StartDocPrinter(printer, 1, ("Zebra Label", None, "RAW"))
            try:
                win32print.StartPagePrinter(printer)
                win32print.WritePrinter(printer, zpl.encode("ascii", errors="replace"))
                win32print.EndPagePrinter(printer)
            finally:
                win32print.EndDocPrinter(printer)
        finally:
            win32print.ClosePrinter(printer)


if __name__ == "__main__":
    PrintLabel().print_label(
        product="7283556630",
        ma="10.21.56996A",
        barcode="7283556630, 10.21.56996A I10131",
        pon="I10131",
        copies=1,
    )