package dsimpl

import (
	"context"
	"fmt"

	"datastore/datastore"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func (svcInfo *ServiceInfo) GetLocations(
	ctx context.Context, request *datastore.GetLocationsRequest) (
	*datastore.GetLocationsResponse, error) {

	response, errCode, reason := svcInfo.Sbe.GetLocations(request)
	if errCode != codes.OK {
		return nil, status.Error(
			errCode, fmt.Sprintf("svcInfo.Sbe.GetLocations() failed: %s", reason))
	}

	return response, nil
}
