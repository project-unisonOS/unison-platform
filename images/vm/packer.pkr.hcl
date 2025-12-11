# Packer template for UnisonOS VM images (QCOW2/VMDK)
# This uses the QEMU builder against a downloaded Ubuntu cloud image.

variable "version" {
  type    = string
  default = "dev"
}

variable "model_flavor" {
  type    = string
  default = "default"
}

variable "base_image_path" {
  type    = string
  default = "ubuntu-24.04-server-cloudimg-amd64.img"
}

variable "ssh_username" {
  type    = string
  default = "ubuntu"
}

variable "ssh_password" {
  type    = string
  default = "ubuntu"
}

source "qemu" "unisonos" {
  communicator    = "ssh"
  ssh_username    = var.ssh_username
  ssh_password    = var.ssh_password
  ssh_timeout     = "30m"
  disk_interface  = "virtio"
  disk_image      = var.base_image_path
  format          = "qcow2"
  headless        = true
  shutdown_command = "echo ${var.ssh_password} | sudo -S shutdown -P now"
  output_directory = "output/qemu"
}

build {
  name    = "unisonos-vm"
  sources = [
    "source.qemu.unisonos"
  ]

  provisioner "shell" {
    script = "provision.sh"
    environment_vars = [
      "UNISON_VERSION=${var.version}",
      "UNISON_MODEL_FLAVOR=${var.model_flavor}"
    ]
  }
}
