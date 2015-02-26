#!/usr/bin/perl

use CGI;
use CGI::Carp 'fatalsToBrowser';

use MD5;

use lib '..';

use btcrpc;
use config;

print "Content-type: text/plain\r\n\r\n";

sub hash2 { hash( $_[0], $config::hash2); }
 
sub hash {
    my $user_id = shift;
    my $secret = shift;
    my $md5 = MD5->new; 
    $md5->reset();
    $md5->add( $user_id . $secret);
    return $md5->hexdigest();
}   

my $address = CGI::param('address');
my $amount = CGI::param('amount');
my $hash = CGI::param('hash');

$address =~ m/^[a-zA-Z0-9]$/ or die "address should be a bitcoin address";
length($address) <= 35 or die "address should be a bitcoin address";

$amount =~ m/^[0-9]+\.[0-9]+$/ or die "amount should be a float";

die unless $hash eq hash2("$address-$amount");

my $tx = btcrpc::send( $address, 0 + $amount, );

print "<tx>$tx</tx>\n";
