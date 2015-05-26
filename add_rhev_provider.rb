#!/usr/bin/env ruby
require 'mechanize'
require 'openssl'

##
#  This script is a prototype to demonstrate a proof of concept.
#
#  Goal:
#     Interact with ManageIQ WebUI to simulate adding a new RHEV provider
#
#  Flow:
#  1) Log into WebUI:  
#     POST /dashboard/authenticate?button=login
#
#  2) Retrieve form for adding a new provider
#     GET /ems_infra/new
#
#  3) Submit form for a new provider
#     POST /ems_infra/create/new?button=add
#  
#  Notes on ManageIQ Authentication
#   - A session cookie is used after login.
#   - The 'referer' needs to be set on most requests
#     ManageIQ limits interaction to a single tab being opened in a web browser
#     I think they are using the referer as one of enforcing this.
#     When we make requests we need to set the refer in the header.
#   - Submitting Form as POST requires csrf-token from meta tag
#
#
#     Related ManageIQ Authorization Code:
#     https://github.com/ManageIQ/manageiq/blob/master/vmdb/app/controllers/application_controller.rb#L1365
#     https://github.com/ManageIQ/manageiq/blob/master/vmdb/app/services/request_referer_service.rb
#
#  Mechanize Ruby Docs:
#  http://www.rubydoc.info/gems/mechanize/Mechanize/

if ARGV.size < 1
  puts "Please re-run with the IP address of the CFME VM"
  exit
end

for env_var in ["OVIRT_IP", "OVIRT_USERNAME", "OVIRT_PASSWORD"] do
  if ENV[env_var].nil?
    puts "Please set the environment variable '#{env_var}' and retry"
    exit
  end
end



CFME_IP=ARGV[0]
CFME_USERNAME="admin"
CFME_PASSWORD="smartvm"

OVIRT_IP=ENV['OVIRT_IP']
OVIRT_HOSTNAME=ENV['OVIRT_IP']
OVIRT_USERNAME=ENV['OVIRT_USERNAME']
OVIRT_PASSWORD=ENV['OVIRT_PASSWORD']


puts "Will add the RHEV provider at #{OVIRT_IP} to the CloudForms VM at #{CFME_IP}"


agent = Mechanize.new
agent.verify_mode = OpenSSL::SSL::VERIFY_NONE

logged_in_page = agent.post("https://#{CFME_IP}/dashboard/authenticate?button=login", 
  {"user_name" => CFME_USERNAME, "user_password" => CFME_PASSWORD})

# The referer is VERY IMPORTANT in manageIQ
# If 'agent.page.uri' is removed in below request it will not function
# We will receive a '403'
#

emfra_new = agent.get("https://#{CFME_IP}/ems_infra/new", [], agent.page.uri)
csrf_token = emfra_new.at('meta[name="csrf-token"]')[:content]

new_provider_form = emfra_new.form

# Careful, had to use ["name"] because .name was not sufficient for setting field 'name'
new_provider_form["name"]="TestName3"
new_provider_form["server_emstype"]="rhevm"

# hostname and ipaddress are added dynamically from javascript when rhevm is selected
# so we need to add these as new fields
new_provider_form.add_field!("hostname", OVIRT_HOSTNAME)
new_provider_form.add_field!("ipaddress", OVIRT_IP)

new_provider_form.port=""
new_provider_form.server_zone="default"

new_provider_form.default_userid=OVIRT_USERNAME
new_provider_form.default_password=OVIRT_PASSWORD
new_provider_form.default_verify=OVIRT_PASSWORD

new_provider_form.metrics_userid=""
new_provider_form.metrics_password=""
new_provider_form.metrics_verify=""

submit_headers = {
  "Referer" => agent.page.uri,
  "X-CSRF-Token" => csrf_token, 
  "Accept" => "text/html,application/xhtml+xml,application/xml,application/json",
  "Accept-Encoding" => "gzip, deflate, sdch",
  "Accept-Language" => "en-US,en",
  "Content-Type" => "application/x-www-form-urlencoded"
}
request_data = new_provider_form.request_data
puts "\nSubmitting request with data:\n\n#{request_data}\n\n"
provider_added = agent.post("https://#{CFME_IP}/ems_infra/create/new?button=add", request_data, submit_headers)

puts "\nReceived response of:\n"
puts "\nBody:\n"
puts provider_added.body
puts "\nHeader:\n"
puts provider_added.header

