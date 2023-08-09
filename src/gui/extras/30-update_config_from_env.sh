#!/bin/bash

CONFIG_FILE="/usr/share/nginx/html/config.json"

perl_script() {
perl - "$CONFIG_FILE" <<'END_OF_PERL'
use strict;
use warnings;

my $CONFIG_FILE = shift @ARGV;

sub add_to_json {
    my ($key, $value, $file) = @_;

    # Read the file into a scalar
    open my $fh, '<', $file or die "Cannot open $file: $!";
    local $/;
    my $content = <$fh>;
    close $fh;

    # Check if key exists and either modify or append
    if ($content =~ /"$key"/) {
        $content =~ s/("$key"\s*:\s*)".*?"/$1"$value"/;
    } else {
        $content =~ s/}\s*$/,"$key":"$value"}/;
    }

    # Write the modified content back to the file
    open my $ofh, '>', $file or die "Cannot write to $file: $!";
    print $ofh $content;
    close $ofh;
}

# Ensure the file has an initial JSON object if it doesn't exist or is empty
unless (-e $CONFIG_FILE) {
    open my $fh, '>', $CONFIG_FILE or die "Cannot create $CONFIG_FILE: $!";
    print $fh '{}';
    close $fh;
}

# Iterate over all environment variables that start with TARANIS_NG
foreach my $key (sort keys %ENV) {
    if ($key =~ /^TARANIS_NG/) {
        my $value = $ENV{$key};
        if (defined $value && $value ne '') {
            add_to_json($key, $value, $CONFIG_FILE);
        }
    }
}
END_OF_PERL
}

perl_script
