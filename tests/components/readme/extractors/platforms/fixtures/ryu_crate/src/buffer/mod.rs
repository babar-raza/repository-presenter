use core::mem::MaybeUninit;

pub struct Buffer {
    bytes: [MaybeUninit<u8>; 24],
}

impl Buffer {
    pub fn new() -> Self {
        let bytes = [MaybeUninit::<u8>::uninit(); 24];
        Buffer { bytes }
    }
}

pub trait Float: Sealed {}
impl Float for f32 {}
impl Float for f64 {}

pub trait Sealed: Copy {
    fn is_nonfinite(self) -> bool;
    fn format_nonfinite(self) -> &'static str;
    unsafe fn write_to_ryu_buffer(self, result: *mut u8) -> usize;
}
