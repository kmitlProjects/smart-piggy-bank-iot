from machine import Pin
import time


class MFRC522:
    OK = 0
    NOTAGERR = 1
    ERR = 2

    REQIDL = 0x26
    REQALL = 0x52
    AUTHENT1A = 0x60
    AUTHENT1B = 0x61

    def __init__(self, spi, cs, rst=None):
        self.spi = spi

        self.cs = cs
        self.cs.init(Pin.OUT, value=1)

        self.rst = rst
        if self.rst is not None:
            self.rst.init(Pin.OUT, value=1)
            self.hard_reset()

        self.init()

    def hard_reset(self):
        if self.rst is None:
            return
        self.rst.value(0)
        time.sleep_ms(50)
        self.rst.value(1)
        time.sleep_ms(50)

    def _wreg(self, reg, val):
        self.cs.value(0)
        self.spi.write(bytes([(reg << 1) & 0x7E]))
        self.spi.write(bytes([val & 0xFF]))
        self.cs.value(1)

    def _rreg(self, reg):
        self.cs.value(0)
        self.spi.write(bytes([((reg << 1) & 0x7E) | 0x80]))
        value = self.spi.read(1)
        self.cs.value(1)
        return value[0]

    def _sflags(self, reg, mask):
        self._wreg(reg, self._rreg(reg) | mask)

    def _cflags(self, reg, mask):
        self._wreg(reg, self._rreg(reg) & (~mask))

    def _tocard(self, cmd, send):
        recv = []
        bits = irq_en = wait_irq = n = 0
        status = self.ERR

        if cmd == 0x0E:
            irq_en = 0x12
            wait_irq = 0x10
        elif cmd == 0x0C:
            irq_en = 0x77
            wait_irq = 0x30

        self._wreg(0x02, irq_en | 0x80)
        self._cflags(0x04, 0x80)
        self._sflags(0x0A, 0x80)
        self._wreg(0x01, 0x00)

        for byte in send:
            self._wreg(0x09, byte)

        self._wreg(0x01, cmd)
        if cmd == 0x0C:
            self._sflags(0x0D, 0x80)

        i = 2000
        while True:
            n = self._rreg(0x04)
            i -= 1
            if not ((i != 0) and not (n & 0x01) and not (n & wait_irq)):
                break

        self._cflags(0x0D, 0x80)

        if i != 0:
            if (self._rreg(0x06) & 0x1B) == 0x00:
                status = self.OK

                if n & irq_en & 0x01:
                    status = self.NOTAGERR

                if cmd == 0x0C:
                    n = self._rreg(0x0A)
                    last_bits = self._rreg(0x0C) & 0x07
                    if last_bits != 0:
                        bits = (n - 1) * 8 + last_bits
                    else:
                        bits = n * 8

                    if n == 0:
                        n = 1
                    if n > 16:
                        n = 16

                    for _ in range(n):
                        recv.append(self._rreg(0x09))
            else:
                status = self.ERR

        return status, recv, bits

    def _crc(self, data):
        self._cflags(0x05, 0x04)
        self._sflags(0x0A, 0x80)

        for byte in data:
            self._wreg(0x09, byte)

        self._wreg(0x01, 0x03)

        i = 0xFF
        while True:
            n = self._rreg(0x05)
            i -= 1
            if not ((i != 0) and not (n & 0x04)):
                break

        return [self._rreg(0x22), self._rreg(0x21)]

    def init(self):
        self.reset()
        self._wreg(0x2A, 0x8D)
        self._wreg(0x2B, 0x3E)
        self._wreg(0x2D, 30)
        self._wreg(0x2C, 0)
        self._wreg(0x15, 0x40)
        self._wreg(0x11, 0x3D)
        self.antenna_on()

    def reset(self):
        self._wreg(0x01, 0x0F)

    def antenna_on(self, on=True):
        if on and not (self._rreg(0x14) & 0x03):
            self._sflags(0x14, 0x03)
        else:
            self._cflags(0x14, 0x03)

    def request(self, mode):
        self._wreg(0x0D, 0x07)
        status, _, bits = self._tocard(0x0C, [mode])

        if (status != self.OK) or (bits != 0x10):
            status = self.ERR

        return status, bits

    def anticoll(self):
        serial_check = 0
        serial = [0x93, 0x20]

        self._wreg(0x0D, 0x00)
        status, recv, _ = self._tocard(0x0C, serial)

        if status == self.OK:
            if len(recv) == 5:
                for index in range(4):
                    serial_check ^= recv[index]
                if serial_check != recv[4]:
                    status = self.ERR
            else:
                status = self.ERR

        return status, recv

    def select_tag(self, serial):
        buf = [0x93, 0x70] + serial[:5]
        buf += self._crc(buf)
        status, _, bits = self._tocard(0x0C, buf)
        return self.OK if (status == self.OK) and (bits == 0x18) else self.ERR

    def auth(self, mode, addr, sect, serial):
        return self._tocard(0x0E, [mode, addr] + sect + serial[:4])[0]

    def stop_crypto1(self):
        self._cflags(0x08, 0x08)

    def read(self, addr):
        data = [0x30, addr]
        data += self._crc(data)
        status, recv, _ = self._tocard(0x0C, data)
        return recv if status == self.OK else None

    def write(self, addr, data):
        buf = [0xA0, addr]
        buf += self._crc(buf)
        status, recv, bits = self._tocard(0x0C, buf)

        if (status != self.OK) or (bits != 4) or ((recv[0] & 0x0F) != 0x0A):
            status = self.ERR
        else:
            buf = list(data[:16])
            while len(buf) < 16:
                buf.append(0)
            buf += self._crc(buf)
            status, recv, bits = self._tocard(0x0C, buf)
            if (status != self.OK) or (bits != 4) or ((recv[0] & 0x0F) != 0x0A):
                status = self.ERR

        return status
